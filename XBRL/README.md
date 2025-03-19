# XBRL Module Refactoring

This document describes the refactoring process of the XBRL module and the steps needed to complete the migration.

## Phase 1: Core Classes and Constants Extraction

### Completed Changes
1. Created `xbrl_core.py` with the following elements:
   - Abstract base class `Neo4jNode`
   - Enum classes: `NodeType`, `RelationType`, `GroupingType`
   - Constants: `PRESENTATION_EDGE_UNIQUE_PROPS`, `CALCULATION_EDGE_UNIQUE_PROPS`
   - `ReportElementClassifier` class with the necessary classification methods

2. Updated `__init__.py` to:
   - Import from new modules first (these override any duplicates from XBRLClasses)
   - Import from XBRLClasses for backward compatibility
   - Added proper error handling for imports
   - Created a wrapper for `process_report` to ensure it works even with dependency issues

3. Created test files:
   - `test_core.py` - Tests for the core functionality
   - `test_import_package.py` - Tests for package imports
   - `test_process_report.py` - Tests for process_report functionality
   - `test_classification_fix.py` - Tests for classification order
   - `test_notebook_simulation.py` - Tests for notebook compatibility

### Fixed Issues
1. **ReportElementClassifier Missing Methods**: Fixed missing classification methods in the `ReportElementClassifier` class that were necessary for node type identification:
   - Added the `classify` method
   - Added helper methods: `check_nillable`, `check_duration`, `get_substitution_group`, `get_local_type`
   - Added classification logic in `_initial_classify` and `_post_classify_single`

2. **Classification Order Preservation**: Ensured that the order of classification checks in `_initial_classify` exactly matches the original implementation:
   1. Basic Concept
   2. Hypercube
   3. Dimension
   4. Member
   5. Abstract
   6. LineItems
   7. Guidance (at the end, not the beginning)
   
   This ensures 100% identical classification results compared to the original code.

3. **Deterministic Iteration**: Added measures to ensure deterministic ordering:
   - Added OrderedDict imports
   - Added documentation about the importance of dictionary and set order
   - Enhanced process_report wrapper for consistent behavior

4. **Import Sequence Control**: Precisely controlled the import sequence in `__init__.py`:
   - First imports core components
   - Then imports the wrapper
   - Finally imports from XBRLClasses

5. **Comprehensive Documentation**: Created detailed documentation in `identical_output_fixes.md` about ensuring identical output when refactoring.

## Phase 2: Basic Node Implementations

### Completed Changes
1. Created `xbrl_basic_nodes.py` with the following classes:
   - `Context`: Represents an XBRL context that provides dimensional qualifiers for facts
   - `Period`: Represents a time period in XBRL (instant or duration)
   - `Unit`: Represents a unit of measure used in XBRL facts
   - `CompanyNode`: Represents a company (issuer) in the XBRL database
   - `ReportNode`: Represents a specific SEC filing report

2. Added extensive documentation to all classes, including:
   - Clear docstrings explaining the purpose of each class
   - Property descriptions
   - Validation logic documentation

3. Updated `__init__.py` to:
   - Import the basic node classes from the new module
   - Include them in the `__all__` list to ensure they're exposed in the package namespace

4. Created test files:
   - `test_basic_nodes.py` - Tests for the basic node implementations
   - `test_package_import_basic_nodes.py` - Tests for importing basic nodes from the package

5. Added refactoring notes in `XBRLClasses.py` to:
   - Document which classes have been moved to new modules
   - Maintain backward compatibility with existing code

### Fixed Issues
1. **Import Order Sensitivity**: Ensured proper import order in `__init__.py` to maintain consistent behavior
2. **Consistent Identifiers**: Ensured u_id generation is identical to original implementation
3. **Comprehensive Testing**: Added tests for all edge cases in node initialization

## Remaining Tasks

1. Continue migration of other classes from XBRLClasses.py:
   - Create `xbrl_concepts.py` for concept-related classes:
     - `Concept`
     - `AbstractConcept`
     - `GuidanceConcept`
   - Create `xbrl_dimensions.py` for dimension-related classes:
     - `Dimension`
     - `Member`
     - `Domain`
     - `Hypercube`
   - Create `xbrl_reporting.py` for reporting classes:
     - `Fact`
     - `Network`
     - `Presentation`
     - `Calculation`

2. Update Neo4jManager to use the new core classes

3. Complete test coverage for all refactored components

## Using This Module

To use this module, make sure you have the necessary dependencies installed:

```bash
pip install neo4j
```

Basic usage:
```python
from XBRL import process_report
from XBRL.Neo4jManager import Neo4jManager

# Initialize Neo4j manager
neo4j = Neo4jManager(uri, username, password)

# Process an XBRL report
report = process_report(instance_url, neo4j)
```

## Jupyter Notebook Usage

If you're using this module in a Jupyter notebook, please refer to the `jupyter_setup_instructions.md` file for detailed setup instructions. In particular, make sure your notebook's kernel has access to the correct Python environment where neo4j is installed. 