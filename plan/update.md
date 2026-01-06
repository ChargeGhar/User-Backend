Analyze my Django app and create a precise, assumption-free refactoring plan.

APP: api/{app_name}/

INPUT:
- Current structure: [paste output of: python structure.py --app {app_name}]
- Line counts and method counts of all files/classes

TASKS:

1. ANALYSIS
   Detect:
   • Files > 300 lines → mark for splitting
   • Classes > 10 methods → mark for refactoring
   • Services with database queries → mark for Repository extraction
   • Services with external API calls → mark for Integration extraction
   • Views with business logic → mark to move to Service layer
   • Serializers > 100 lines or complex validation → mark to split or extract validators
   • Code smells, anti-patterns, or inconsistent naming

2. REFACTORING PROPOSAL
   Provide:
   • Current vs Proposed folder structure
   • File splitting plan
   • Service layer improvements (Repositories, Integrations, Utils, Rules)
   • Serializer refactoring (Input/Output/Nested)
   • Import changes required
   • Backward compatibility plan

3. EXECUTION PLAN
   Break into clear phases:
   • Phase 1: [tasks + estimated time]
   • Phase 2: [tasks + estimated time]
   • Phase 3: [tasks + estimated time]

4. VALIDATION CHECKLIST
   • Commands to verify changes (e.g., manage.py check, import tests)
   • Expected final file structure

RULES & STANDARDS:
- Services: max 10 methods; database queries → Repository; external APIs → Integration
- Views: only validate request, check permissions, call service, format response
- Serializers: split Input/Output if >100 lines; extract validators if complex
- Naming conventions: consistent across apps (services, repositories, integrations, utils, serializers)
- File size thresholds: service > 300 lines, view > 400 lines, serializer > 300 lines
- No assumptions about logic, dependencies, or content — base analysis only on structure, line/method counts, and Django best practices
- Maintain backward compatibility with import paths

OUTPUT FORMAT:
══════════════════════════════════════════════
📊 REFACTORING ANALYSIS: api/{app_name}/

🔍 FINDINGS:
• [list all detected issues with files/classes]

📋 PROPOSAL:
CURRENT STRUCTURE:
api/{app_name}/
├── [current structure]

PROPOSED STRUCTURE:
api/{app_name}/
├── [proposed structure]

FILE SPLITTING PLAN:
• [file/class → new files with reasons]

SERVICE LAYER IMPROVEMENTS:
• [repositories/integrations/utils/rules]

IMPORT & BACKWARD COMPATIBILITY:
• [required changes + strategy]

EXECUTION PLAN:
Phase 1: [tasks]
Phase 2: [tasks]
Phase 3: [tasks]

VALIDATION CHECKLIST:
• python manage.py check
• import tests for serializers/services
• verify URLs, circular dependencies, backward compatibility
══════════════════════════════════════════════
