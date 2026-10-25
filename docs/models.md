# Rates context
## RatePeriod
- name: string
- starts_on: date
- ends_on: date

## RateCategory
- category: string enum regular|premium

## DrywallRate
- height: string enum
- rate_category: RateCategory
- rate: decimal required
- rate_period: RatePeriod

## SprinklersRate
- rate: decimal required
- unpaid_quantity: int
- rate_period: RatePeriod

## PotlightsRate
- rate: decimal required
- unpaid_quantity: int
- rate_period: RatePeriod

## JmouldRate
- rate: decimal required
- rate_period: RatePeriod

## InsulationRate
- rate: decimal required
- rate_period: RatePeriod


# Activity context

## Activity
- name: string required unique
- description: string optional

## ActivityLog
- activity: Activity
- start: datetime require
- end: datetime optional
- unit: Unit required

# Project context
## Project
- name: string
- drywall_company: string
- general_contractor: string

# Unit tracking context
## Unit
- number: string required
- potlights_count: number optional
- sprinklers_count: number optional
- status: string enum active | on_hold | completed
- project: Project
- height: string enum (8,9] | (9,10] | (10,11], (11,12] required
- sheet_count: UnitSheetCount[]

## DrywallMaterial
- drywall_type: string
- length_feet: int
- rate_category: RateCategory

## UnitSheetCount
- drywall_material: DrywallMaterial
- count: int
- unit: Unit
- square_footage: int
- payable_amount: int

### Rules
1. only one unit can have status active

# Payments context





