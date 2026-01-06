"""
Generate Mermaid ER Diagrams for Django projects
"""
import os
import sys
import django

# Setup Django settings - adjust this to your project
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.config.settings")
django.setup()

from django.apps import apps
from django.db import models


def model_to_mermaid(output_file="chargeghar_erd.md", exclude_apps=None):
    """
    Generate a Mermaid ER diagram from all Django models.
    
    Args:
        output_file: Output markdown file name
        exclude_apps: List of app names to exclude (e.g., ['admin', 'auth', 'contenttypes'])
    """
    if exclude_apps is None:
        # Default Django apps and third-party apps to exclude
        exclude_apps = [
            'admin', 'auth', 'contenttypes', 'sessions', 
            'messages', 'staticfiles', 'sites', 'silk',
            'axes', 'social_django', 'django_celery_beat',
            'django_celery_results', 'rest_framework',
            'drf_spectacular', 'corsheaders', 'storages',
            'admin_interface',  # Theme model
            'token_blacklist',  # JWT tokens
            'account',  # allauth
            'socialaccount',  # allauth social
            'allauth',
        ]
    
    models_list = list(apps.get_models())
    models_data = []
    relations = []
    
    # Filter out excluded apps
    filtered_models = []
    for model in models_list:
        app_label = model._meta.app_label
        if app_label not in exclude_apps:
            filtered_models.append(model)
    
    models_list = filtered_models
    print(f"Found {len(models_list)} models to process")
    
    for model in models_list:
        model_dict = {}
        model_fields = []
        for field in model._meta.get_fields():
            model_fields.append(field)
        model_dict[model.__name__] = model_fields
        models_data.append(model_dict)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("## ChargeGhar ER Diagram\n\n```mermaid\nerDiagram\n")
        
        for model in models_data:
            for model_name in model:
                f.write(f"    {model_name} {{\n")
                for field in model[model_name]:
                    try:
                        field_type = field.get_internal_type()
                        field_name = field.name
                        
                        # Handle relationships
                        if hasattr(field, 'related_model') and field.related_model:
                            # Check if related model is in our list
                            if field.related_model in models_list:
                                field_related_model = field.related_model.__name__
                                field_model = field.model.__name__
                                
                                if field_type == 'ForeignKey':
                                    relationship = "||--|{"
                                elif field_type == "ManyToManyField":
                                    relationship = "}|--|{"
                                elif field_type == 'OneToOneField':
                                    relationship = "||--||"
                                else:
                                    relationship = "||--||"
                                
                                relation_line = f"    {field_model} {relationship} {field_related_model} : {field_name}\n"
                                if relation_line not in relations:
                                    relations.append(relation_line)
                        else:
                            # Regular field - write to diagram
                            f.write(f"        {field_type} {field_name}\n")
                    except AttributeError:
                        # Handle reverse relations and other special fields
                        pass
                f.write("    }\n")
        
        # Write all relationships at the end
        f.write("\n")
        f.writelines(relations)
        f.write("```\n")
    
    print(f"ER Diagram generated -> {output_file}")


def main():
    """Run the ER diagram generator"""
    # You can customize excluded apps here
    exclude = [
        'admin', 'auth', 'contenttypes', 'sessions',
        'messages', 'staticfiles', 'sites', 'silk',
        'axes', 'social_django', 'django_celery_beat',
        'django_celery_results', 'rest_framework',
        'drf_spectacular', 'corsheaders', 'storages',
        'admin_interface',  # Theme model
        'token_blacklist',  # JWT tokens
        'account',  # allauth
        'socialaccount',  # allauth social
        'allauth',
    ]
    
    model_to_mermaid(
        output_file="chargeghar_erd.md",
        exclude_apps=exclude
    )


if __name__ == "__main__":
    main()
