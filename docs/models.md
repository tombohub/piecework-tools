# Activity

## Fields
- name: string required unique
- description: string optional

# Project

## Fields
- name: string
- drywall_company: string
- general_contractor: string

# Unit

## Fields
- number: string required
- potlights_count: number optional
- sprinklers_count: number optional
- status: string enum active | on_hold | completed
- project: Project

## Rules
1. only one unit can have status active

# ActivityLog

## Fields
- activity: Activity
- start: datetime require
- end: datetime optional
- unit: Unit required


