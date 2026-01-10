#!/usr/bin/env python3
"""
PowerBank Static Table Extractor Tool
Extracts only the static/configuration tables from chargeghar_erd.md
Helps stay within project boundaries and requirements.

Usage:
    python extract_tables.py                           # Interactive mode
    python extract_tables.py --list                    # List static tables
    python3 extract_tables.py --structure Country       # Show table structure
    python3 extract_tables.py --model PaymentMethod     # Generate Django model
    python extract_tables.py --all-structures          # Show all structures
    python extract_tables.py --validate                # Validation only
"""

import re
import sys
import argparse
from typing import List, Dict, Set
from pathlib import Path

class PowerBankTableExtractor:
    """Extracts ALL tables from ER diagram - Simple and Powerful for ongoing context."""
    
    def __init__(self, er_diagram_path: str = "/chargeghar_erd.md"):
        self.er_diagram_path = Path(er_diagram_path)
        self.all_tables: Set[str] = set()
        self.table_definitions: Dict[str, Dict] = {}
        
    def load_er_diagram(self) -> str:
        """Load the ER diagram markdown content."""
        try:
            with open(self.er_diagram_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Error: {self.er_diagram_path} not found")
            return ""
    
    def extract_tables(self, content: str) -> None:
        """Extract ALL table definitions from mermaid ER diagram - No limits."""
        # Pattern to match table definitions
        table_pattern = r'(\w+)\s*\{([^}]+)\}'
        
        matches = re.findall(table_pattern, content, re.MULTILINE | re.DOTALL)
        
        for table_name, fields_block in matches:
            fields = []
            for line in fields_block.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('%'):
                    fields.append(line)
            
            self.table_definitions[table_name] = {
                'fields': fields,
            }
            self.all_tables.add(table_name)
    
    def get_all_tables(self) -> Dict[str, Dict]:
        """Get ALL tables from ER diagram - Simple and complete."""
        return self.table_definitions
    
    def get_table_list(self) -> List[str]:
        """Get simple list of all available tables."""
        return sorted(list(self.all_tables))
    
    def print_all_tables_summary(self) -> None:
        """Print summary of ALL tables found - Simple overview."""
        print("="*80)
        print("POWERBANK ALL TABLES SUMMARY")
        print("="*80)
        print(f"Total tables found in ER diagram: {len(self.table_definitions)}")
        
        print(f"\n📋 ALL AVAILABLE TABLES:")
        for i, table in enumerate(sorted(self.all_tables), 1):
            fields = self.table_definitions[table]['fields']
            print(f"{i:2d}. {table} ({len(fields)} fields)")
        
        print(f"\n✅ Extract ANY table using: python extract_tables.py --structure <TableName>")
        print(f"✅ Preview model using: python extract_tables.py --model <TableName>")
        print(f"✅ No limitations - All tables available")
    
    def preview_model_before_creation(self, table_name: str) -> Dict:
        """Preview what the Django model will look like BEFORE creation."""
        if table_name not in self.table_definitions:
            return {"error": f"Table {table_name} not found in ER diagram"}
        
        structure = self.get_table_structure(table_name)
        model_code = self.generate_accurate_model(table_name)
        
        preview = {
            'table_name': table_name,
            'field_count': len(structure['fields']),
            'relationship_count': len(structure.get('relationships', [])),
            'model_preview': model_code,
            'structure_details': structure,
            'ready_for_creation': True
        }
        
        return preview
    
    def get_table_structure(self, table_name: str) -> Dict:
        """Get detailed table structure for accurate model creation."""
        if table_name not in self.table_definitions:
            return {"error": f"Table {table_name} not found in ER diagram"}
        
        table_def = self.table_definitions[table_name]
        fields = table_def['fields']
        
        parsed_fields = []
        relationships = []
        
        for field in fields:
            field_info = self._parse_field(field)
            if field_info['type'] == 'foreign_key':
                relationships.append(field_info)
            else:
                parsed_fields.append(field_info)
        
        return {
            'table_name': table_name,
            'fields': parsed_fields,
            'relationships': relationships,
            'raw_fields': fields,
            'total_fields': len(parsed_fields) + len(relationships)
        }
    
    def _parse_field(self, field_line: str) -> Dict:
        """Parse individual field from ER diagram."""
        field_line = field_line.strip()
        
        # Parse field components
        parts = field_line.split()
        if len(parts) < 2:
            return {'raw': field_line, 'type': 'unknown'}
        
        field_type = parts[0]
        field_name = parts[1]
        constraints = ' '.join(parts[2:]) if len(parts) > 2 else ''
        
        # Determine Django field type
        django_field = self._map_to_django_field(field_type, field_name, constraints)
        
        return {
            'name': field_name,
            'er_type': field_type,
            'django_field': django_field['field'],
            'django_options': django_field['options'],
            'constraints': constraints,
            'is_primary_key': 'PK' in constraints,
            'is_foreign_key': 'FK' in constraints,
            'is_unique': 'UK' in constraints or 'unique' in constraints.lower(),
            'is_nullable': 'nullable' in constraints.lower(),
            'has_default': 'default' in constraints.lower(),
            'type': 'foreign_key' if 'FK' in constraints else 'regular',
            'raw': field_line
        }
    
    def _map_to_django_field(self, er_type: str, field_name: str, constraints: str) -> Dict:
        """Map ER diagram field type to Django field."""
        er_type = er_type.lower()
        field_name = field_name.lower()
        constraints = constraints.lower()
        
        # Foreign Key
        if 'fk' in constraints:
            related_model = self._extract_fk_model(constraints)
            return {
                'field': 'models.ForeignKey',
                'options': f"'{related_model}', on_delete=models.CASCADE"
            }
        
        # Primary Key (UUID)
        if er_type == 'uuid' and 'pk' in constraints:
            return {
                'field': 'models.UUIDField',
                'options': 'primary_key=True, default=uuid.uuid4, editable=False'
            }
        
        # String fields
        if er_type == 'string':
            if 'email' in field_name:
                return {'field': 'models.EmailField', 'options': ''}
            elif 'url' in field_name or 'link' in field_name:
                return {'field': 'models.URLField', 'options': ''}
            elif 'phone' in field_name:
                return {'field': 'models.CharField', 'options': 'max_length=20'}
            else:
                max_length = 255
                if 'code' in field_name:
                    max_length = 10
                elif 'name' in field_name:
                    max_length = 100
                return {'field': 'models.CharField', 'options': f'max_length={max_length}'}
        
        # Text fields
        if er_type == 'text':
            return {'field': 'models.TextField', 'options': ''}
        
        # Boolean fields
        if er_type == 'boolean':
            default_val = 'True' if 'default true' in constraints else 'False'
            return {'field': 'models.BooleanField', 'options': f'default={default_val}'}
        
        # Integer fields
        if er_type == 'integer':
            return {'field': 'models.IntegerField', 'options': ''}
        
        # Decimal fields
        if er_type == 'decimal':
            return {'field': 'models.DecimalField', 'options': 'max_digits=10, decimal_places=2'}
        
        # Enum fields
        if er_type == 'enum':
            choices = self._extract_enum_choices(constraints)
            return {'field': 'models.CharField', 'options': f'max_length=50, choices={choices}'}
        
        # DateTime fields
        if er_type == 'datetime':
            if 'created_at' in field_name:
                return {'field': 'models.DateTimeField', 'options': 'auto_now_add=True'}
            elif 'updated_at' in field_name:
                return {'field': 'models.DateTimeField', 'options': 'auto_now=True'}
            else:
                return {'field': 'models.DateTimeField', 'options': ''}
        
        # Date fields
        if er_type == 'date':
            return {'field': 'models.DateField', 'options': ''}
        
        # JSON fields
        if er_type == 'json':
            return {'field': 'models.JSONField', 'options': 'default=dict'}
        
        # Default
        return {'field': 'models.CharField', 'options': 'max_length=255'}
    
    def _extract_fk_model(self, constraints: str) -> str:
        """Extract the related model name from FK constraint."""
        # This is a simple extraction - might need refinement
        if 'user_id' in constraints:
            return 'User'
        elif 'station_id' in constraints:
            return 'Station'
        elif 'payment_method_id' in constraints:
            return 'PaymentMethod'
        else:
            return 'RelatedModel'  # Placeholder
    
    def _extract_enum_choices(self, constraints: str) -> str:
        """Extract enum choices from constraint string."""
        # Look for quoted values in constraints
        import re
        matches = re.findall(r'"([^"]*)"', constraints)
        if matches:
            choices = [(choice.upper(), choice.title()) for choice in matches]
            return str(choices)
        return '[("ACTIVE", "Active"), ("INACTIVE", "Inactive")]'  # Default
    
    def generate_accurate_model(self, table_name: str) -> str:
        """Generate accurate Django model with clear preview format."""
        structure = self.get_table_structure(table_name)
        
        if 'error' in structure:
            return structure['error']
        
        # Generate imports needed
        imports = ["from django.db import models", "import uuid"]
        if any(field['django_field'] == 'models.JSONField' for field in structure['fields']):
            imports.append("from django.contrib.postgres.fields import JSONField")
        
        model_code = '\n'.join(imports) + '\n\n'
        
        # Generate model class with clear structure
        model_code += f'class {table_name}(BaseModel):\n'
        model_code += f'    """\n    {table_name} - PowerBank Table\n'
        model_code += f'    Fields: {structure["total_fields"]}\n'
        model_code += f'    Relationships: {len(structure["relationships"])}\n    """\n'
        
        # Generate fields with comments
        for field in structure['fields']:
            if field['is_primary_key'] and field['name'] == 'id':
                continue  # Skip, handled by BaseModel
            
            field_line = f"    {field['name']} = {field['django_field']}("
            if field['django_options']:
                field_line += field['django_options']
            field_line += ")"
            
            # Add nullable option
            if field['is_nullable'] and 'null=True' not in field_line:
                field_line = field_line.replace(')', ', null=True, blank=True)')
            
            # Add unique option
            if field['is_unique'] and 'unique=True' not in field_line:
                field_line = field_line.replace(')', ', unique=True)')
            
            # Add field comment
            field_line += f"  # {field['er_type']}"
            
            model_code += field_line + '\n'
        
        # Generate relationships with comments
        for rel in structure['relationships']:
            rel_line = f"    {rel['name']} = {rel['django_field']}({rel['django_options']})"
            if rel['is_nullable']:
                rel_line = rel_line.replace(')', ', null=True, blank=True)')
            rel_line += f"  # FK -> {rel['django_options']}"
            model_code += rel_line + '\n'
        
        # Generate Meta class
        model_code += f'\n    class Meta:\n'
        model_code += f'        db_table = "{table_name.lower()}s"\n'
        model_code += f'        verbose_name = "{table_name}"\n'
        model_code += f'        verbose_name_plural = "{table_name}s"\n'
        
        # Generate __str__ method
        name_field = next((f['name'] for f in structure['fields'] if 'name' in f['name']), 'id')
        model_code += f'\n    def __str__(self):\n'
        model_code += f'        return str(self.{name_field})\n'
        
        return model_code
    
    def print_model_preview(self, table_name: str) -> None:
        """Print complete model preview before creation."""
        preview = self.preview_model_before_creation(table_name)
        
        if 'error' in preview:
            print(f"❌ Error: {preview['error']}")
            return
        
        print(f"\n{'='*80}")
        print(f"DJANGO MODEL PREVIEW: {table_name}")
        print(f"{'='*80}")
        print(f"📊 Fields: {preview['field_count']}")
        print(f"🔗 Relationships: {preview['relationship_count']}")
        print(f"✅ Ready for creation: {preview['ready_for_creation']}")
        
        print(f"\n📋 DJANGO MODEL CODE:")
        print(f"{'='*60}")
        print(preview['model_preview'])
        
        print(f"{'='*60}")
        print(f"🎯 To use this model:")
        print(f"   1. Copy the code above")
        print(f"   2. Add to your models.py")
        print(f"   3. Run makemigrations")
        print(f"   4. Run migrate")
        
        return preview
    
    def print_table_structure(self, table_name: str) -> None:
        """Print detailed table structure for review before model creation."""
        structure = self.get_table_structure(table_name)
        
        if 'error' in structure:
            print(f"❌ {structure['error']}")
            return
        
        print(f"\n{'='*80}")
        print(f"TABLE STRUCTURE: {table_name}")
        print(f"Total Fields: {structure['total_fields']}")
        print(f"{'='*80}")
        
        print(f"\n📋 REGULAR FIELDS ({len(structure['fields'])} fields):")
        for i, field in enumerate(structure['fields'], 1):
            nullable = " [NULL]" if field['is_nullable'] else " [NOT NULL]"
            unique = " [UNIQUE]" if field['is_unique'] else ""
            pk = " [PK]" if field['is_primary_key'] else ""
            
            print(f"  {i:2d}. {field['name']} -> {field['django_field']}")
            print(f"      ER Type: {field['er_type']}")
            print(f"      Options: {field['django_options'] or 'None'}")
            print(f"      Flags: {nullable}{unique}{pk}")
            print()
        
        if structure['relationships']:
            print(f"🔗 RELATIONSHIPS ({len(structure['relationships'])} relationships):")
            for i, rel in enumerate(structure['relationships'], 1):
                nullable = " [NULL]" if rel['is_nullable'] else " [NOT NULL]"
                print(f"  {i:2d}. {rel['name']} -> {rel['django_field']}")
                print(f"      Target: {rel['django_options']}")
                print(f"      Flags: {nullable}")
                print()
        
        print(f"📝 RAW ER FIELDS:")
        for field in structure['raw_fields']:
            print(f"  - {field}")
        
        print(f"\n🎯 Next steps:")
        print(f"   • Use: python extract_tables.py --model {table_name}")
        print(f"   • This will show you the exact Django model code")
        print(f"   • Review before adding to your models.py")
    
    def list_all_available_tables(self) -> None:
        """List all available tables with field counts."""
        print("="*80)
        print("ALL AVAILABLE TABLES FROM POWERBANK ER DIAGRAM")
        print("="*80)
        
        tables = sorted(self.all_tables)
        for i, table in enumerate(tables, 1):
            field_count = len(self.table_definitions[table]['fields'])
            print(f"  {i:2d}. {table} ({field_count} fields)")
        
        print(f"\n📊 Total: {len(tables)} tables available")
        print(f"🎯 Use: python extract_tables.py --structure <TableName>")
        print(f"🎯 Use: python extract_tables.py --model <TableName>")
        print(f"✅ No restrictions - Extract ANY table you need")
    
    def validate_static_table_requirements(self) -> Dict:
        """Validate that we have all required static tables with correct structure."""
        required_tables = [
            'AppConfig', 'Country', 'PaymentMethod', 'StationAmenity',
            'RentalPackage', 'ContentPage', 'NotificationTemplate', 
            'NotificationRule', 'Achievement', 'AppVersion', 'Banner',
            'FAQ', 'ContactInfo', 'AppUpdate'
        ]
        
        validation_results = {
            'found_tables': [],
            'missing_tables': [],
            'validation_errors': [],
            'total_required': len(required_tables),
            'total_found': 0
        }
        
        for table in required_tables:
            if table in self.table_definitions:
                validation_results['found_tables'].append(table)
                # Basic validation
                structure = self.get_table_structure(table)
                if not structure['fields']:
                    validation_results['validation_errors'].append(f"{table}: No fields found")
            else:
                validation_results['missing_tables'].append(table)
        
        validation_results['total_found'] = len(validation_results['found_tables'])
        
        return validation_results


def main():
    """Main function - Simple and powerful table extraction."""
    parser = argparse.ArgumentParser(
        description='PowerBank Table Extractor - Extract ANY table from ER diagram',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_tables.py                           # List all available tables
  python extract_tables.py --list                    # List all tables
  python extract_tables.py --structure Country       # Show table structure  
  python extract_tables.py --model PaymentMethod     # Preview Django model
  python extract_tables.py --preview User            # Complete model preview
  python extract_tables.py --all                     # Show all structures
        """
    )
    
    parser.add_argument('--list', action='store_true', 
                       help='List all available tables')
    parser.add_argument('--structure', type=str, metavar='TABLE_NAME',
                       help='Show detailed structure for specific table')
    parser.add_argument('--model', type=str, metavar='TABLE_NAME',
                       help='Show Django model code for specific table')
    parser.add_argument('--preview', type=str, metavar='TABLE_NAME',
                       help='Complete model preview with structure and code')
    parser.add_argument('--all', action='store_true',
                       help='Show all table structures')
    
    args = parser.parse_args()
    
    # If no arguments provided, show all tables
    if len(sys.argv) == 1:
        args.list = True
    
    extractor = PowerBankTableExtractor("chargeghar_erd.md")
    
    # Load and parse ER diagram
    content = extractor.load_er_diagram()
    if not content:
        return
    
    # Extract ALL tables
    extractor.extract_tables(content)
    
    # Handle commands
    if args.list:
        extractor.list_all_available_tables()
        return
    
    if args.structure:
        extractor.print_table_structure(args.structure)
        return
    
    if args.model:
        model_code = extractor.generate_accurate_model(args.model)
        print(f"\n{'='*80}")
        print(f"DJANGO MODEL CODE: {args.model}")
        print(f"{'='*80}")
        print(model_code)
        return
    
    if args.preview:
        extractor.print_model_preview(args.preview)
        return
    
    if args.all:
        tables = extractor.get_table_list()
        for i, table in enumerate(tables, 1):
            print(f"\n[{i}/{len(tables)}]")
            extractor.print_table_structure(table)
            if i < len(tables):
                print("\n" + "-"*80)
        return


# Helper functions for programmatic usage - Simple and clean
def extract_table_structure(table_name: str) -> Dict:
    """Extract table structure for use in other scripts."""
    try:
        extractor = PowerBankTableExtractor("chargeghar_erd.md")
        content = extractor.load_er_diagram()
        if not content:
            return {"error": "Could not load ER diagram"}
        
        extractor.extract_tables(content)
        return extractor.get_table_structure(table_name)
    
    except Exception as e:
        return {"error": str(e)}


def get_all_available_tables() -> List[str]:
    """Get list of all tables programmatically."""
    try:
        extractor = PowerBankTableExtractor("chargeghar_erd.md")
        content = extractor.load_er_diagram()
        if not content:
            return []
        
        extractor.extract_tables(content)
        return extractor.get_table_list()
    
    except Exception as e:
        print(f"Error: {e}")
        return []


def preview_model(table_name: str) -> Dict:
    """Preview Django model for any table programmatically."""
    try:
        extractor = PowerBankTableExtractor("chargeghar_erd.md")
        content = extractor.load_er_diagram()
        if not content:
            return {"error": "Could not load ER diagram"}
        
        extractor.extract_tables(content)
        return extractor.preview_model_before_creation(table_name)
    
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    main()
