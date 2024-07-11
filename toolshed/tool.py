import json
import inspect
from typing import get_type_hints, Callable
import functools
import jsonschema
from django.contrib.postgres.fields import ArrayField
from django.db import models

class ToolObj:
    def __init__(
        self,
        name:str,
        description:str,
        func:Callable,
        schema_validation:bool=True,
        retry_on_fail:bool=True,
        max_fails:int=0,
        reset_max_fails_on_success:bool=True) -> None:
        
        self.name = name
        self.description = description
        self.schema = ToolObj.generate_json_schema_from_function(func, self.description)
        self.func = func
        self.tool ={
            "type": "function",
            "function": self.schema
        }
        self._schema_validation = schema_validation
        self.retry_on_fail = retry_on_fail
        self.max_fails=max_fails
        self.reset_max_fails_on_success = reset_max_fails_on_success
        self._fails = 0
        self._active = True

    @staticmethod
    def generate_json_schema_from_function(func, description = ""):
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        sig = inspect.signature(func)
        type_hints = get_type_hints(func)

        for param_name, param in sig.parameters.items():
            param_type = type_hints.get(param_name, str)  # Default to string if no type hint
            if issubclass(param_type, models.Model):
                schema['properties'][param_name] = ToolObj.generate_json_schema_from_model(param_type)
            else:
                # Map Python types to JSON Schema types
                if param_type == int:
                    json_type = 'integer'
                elif param_type == str:
                    json_type = 'string'
                elif param_type == bool:
                    json_type = 'boolean'
                elif param_type == float:
                    json_type = 'number'
                else:
                    json_type = 'string'  # Default to string for other types

                schema['properties'][param_name] = {"type": json_type}

            if param.default == param.empty:
                schema['required'].append(param_name)
        with open('sch.json', 'w') as f:
                        json.dump({"name": func.__name__,"description": description,"parameters":schema}, f)
        return {"name": func.__name__,"description": description,"parameters":schema}

    @staticmethod
    def map_django_field_to_type(djangoField):
        if djangoField == 'IntegerField':
            json_type = 'integer'
        elif djangoField in ['CharField', 'TextField']:
            json_type = 'string'
        elif djangoField == 'BooleanField':
            json_type = 'boolean'
        elif djangoField == 'FloatField':
            json_type = 'number'     
        else:
            json_type = 'string'  # Default to string for other types
        return json_type
    @staticmethod
    def generate_json_schema_from_model(model_class : models.Model):
        
        schema = {
            "title": model_class.__name__,
            "type": "object",
            "properties": {},
            "required": []
        }
        models_to_process = [(model_class._meta.get_fields(),schema["properties"], schema["required"])]

        while models_to_process:
            all_fields, current_schema, current_required = models_to_process.pop(0)
            fields = [field for field in all_fields if not field.auto_created]

            while fields:
                field_schema = {}
                field = fields.pop(0)
                field_name = field.name

                if isinstance(field, (models.ForeignKey, models.OneToOneField)):
                    referenced_model = field.related_model
                    related_schema = {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                    current_schema[field_name] = related_schema
                    models_to_process.append((referenced_model._meta.get_fields(), related_schema["properties"], related_schema.get("required", [])))
                
                elif isinstance(field, (models.ManyToManyField)):
                    referenced_model = field.related_model
                    related_schema = {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
            
                    child_fields = referenced_model._meta.get_fields()
                    current_schema[field_name] = related_schema
                    models_to_process.append((child_fields, related_schema["items"]["properties"], related_schema["items"]["required"]))
                
                elif isinstance(field,ArrayField):
                    field.base_field.name = "items"
                    child_fields=[field.base_field]
                    related_schema = {
                    "type": "array",
                    "items": {}
                    }
                    current_schema[field_name] = related_schema
                    models_to_process.append((child_fields, related_schema["items"], []))
                else:
                    json_type = ToolObj.map_django_field_to_type(field.get_internal_type()) 
                    field_schema["type"] = json_type
            
                    if field.default is not models.NOT_PROVIDED:
                        field_schema["default"] = field.default
                    if field.choices:
                        field_schema["enum"] =[t[0] for t in field.choices]
                    if field.help_text:
                        field_schema["description"] = field.help_text
                
                    current_schema[field_name] = field_schema
                if not field.blank:
                    current_required.append(field.name)
        return schema

class Tool:
    tools : list[ToolObj] = []

    def __init__(self, description):
        self.description = description

    def __call__(self, func):
        
        self.tools.append(ToolObj(func.__name__, self.description, func))

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            print("wrapper")
            return func(*args, **kwargs)
        
        return wrapper

    def runTools(self, tool_calls):
        tool_outputs = []
        for call in tool_calls:
            tool_call_id = call.id
            tool_function_name = call.function.name
            tool_function_arguments = json.loads(call.function.arguments)
            for t in Tool.tools:
                if t.name == tool_function_name:
                    try:
                        if t._schema_validation:
                            jsonschema.validate(tool_function_arguments, t.schema["parameters"])
                        #write_schema_to_file(t.schema)
                        #write_arguments_to_file(tool_function_arguments)
                    except jsonschema.ValidationError as e:
                        Tool.handle_validation_error(tool_outputs,tool_call_id,t,e)
                        continue
                    if (t.reset_max_fails_on_success):
                        t._fails=0
                    tool_outputs.append({
                        "tool_call_id": tool_call_id,
                        "output": json.dumps(t.func(**tool_function_arguments))
                    })
        return tool_outputs

    @staticmethod
    def handle_validation_error(tool_outputs, tool_call_id, t:ToolObj, e:jsonschema.ValidationError):
        if(t.retry_on_fail and (t.max_fails==0 or t._fails < t.max_fails)):
            tool_outputs.append({
                "tool_call_id": tool_call_id,
                "output": json.dumps({"error": e.message, "path": e.json_path, f"instruction":"please correct the error"})
                })
            t._fails+=1
        else:
            t._active=False
            tool_outputs.append({
                "tool_call_id": tool_call_id,
                "output": json.dumps({"error": e.message, "path": e.json_path, "instruction":f"Max errors exceeded for functoin {t.name}. Please Do not call again."})
                })
    
    
    def write_schema_to_file(schema):
        with open('schema.json', 'w') as f:
            json.dump(schema, f)
    def write_arguments_to_file(args):
        with open('args.json', 'w') as f:
            json.dump(args, f)




    

