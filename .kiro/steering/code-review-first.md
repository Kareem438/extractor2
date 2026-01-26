# Code Review First - CRITICAL RULE

## ALWAYS CHECK EXISTING CODE BEFORE IMPLEMENTING

Before implementing ANY feature or making ANY changes:

1. **Search for existing implementations** - Use `grepSearch` to find if similar functionality already exists
2. **Read the relevant files** - Understand the current code structure and patterns
3. **Identify existing functions/components** - Don't create duplicates of what already exists
4. **Understand the data flow** - Check how data is currently being passed and stored
5. **Check for existing UI elements** - Buttons, forms, sections that might already exist

## Common Mistakes to Avoid

- Creating new buttons when they already exist (e.g., "Ready for Extraction" button)
- Adding new API endpoints when existing ones can be extended
- Creating new database columns when they already exist
- Adding new CSS classes when existing ones can be reused
- Creating new functions when existing ones just need modification

## Before Writing Code, Ask:

1. Does this functionality already exist somewhere?
2. Can I extend/modify existing code instead of creating new?
3. Will my changes conflict with or duplicate existing code?
4. Am I following the existing patterns in the codebase?

## Search Strategy

1. Search for the feature name (e.g., "ready for extraction", "skip page")
2. Search for related function names (e.g., "toggle", "validate", "check")
3. Search for UI element IDs and class names
4. Search for API endpoint patterns
5. Read the files that are most likely to contain the functionality

## This Rule Exists Because

Creating duplicates:
- Breaks existing functionality
- Confuses the codebase
- Wastes time fixing conflicts
- Makes maintenance harder
- Frustrates the user
