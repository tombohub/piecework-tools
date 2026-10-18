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
- is_finished: bool required
- project: Project

# ActivityLog

## Fields
- activity: Activity

