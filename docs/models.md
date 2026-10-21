# Activity
- name: string required unique
- description: string optional

# Project
- name: string
- drywall_company: string
- general_contractor: string

# Unit
- number: string required
- potlights_count: number optional
- sprinklers_count: number optional
- status: string enum active | on_hold | completed
- project: Project

## Rules
1. only one unit can have status active

# PieceworkRate:
- payable_item: string required (drywall, sprinkler etc)
- measurement_unit: string required (sqft | linear_feet | piece)
- height: string enum (8,9] | (9,10] | (10,11], (11,12] required
- rate: decimal required
- included_quantity: integer required (5 sprinklers are not payable)
- drywall_type: string required, for premium rates
- start_date: date required, inclusive
- end_date: date required, inclusive



# ActivityLog
- activity: Activity
- start: datetime require
- end: datetime optional
- unit: Unit required


