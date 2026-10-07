# Cloud Advisor Insights

Build the V1 frontend for a project called “Cloud Advisor”.

PROJECT DESCRIPTION

Cloud Advisor is a multi-cloud FinOps cost intelligence and optimization platform for AWS, Microsoft Azure, and Google Cloud Platform.

The purpose of the system is to help users:
- monitor cloud spending
- understand where money is being spent
- identify potentially unused services
- detect low-utilization resources
- visualize cost and usage trends
- identify cost-optimization opportunities
- provide actionable recommendations

The current system uses:
- React frontend
- Flask backend services
- MySQL database
- AWS Cost Explorer / Azure Cost Management / GCP billing integrations
- provider-specific cost and usage data
- unused-service analysis
- low-utilization analysis
- recommendation logic

The overall data flow is:

AWS / Azure / GCP
        ↓
Cloud data ingestion
        ↓
MySQL / normalized data
        ↓
Cost & utilization analysis
        ↓
Unused / low-utilization detection
        ↓
Recommendations
        ↓
User dashboard

This V1 frontend should focus only on the currently important product experience. Future features such as a Rules Engine, ML models and LLM recommendation layer may be added later.

==================================================
V1 SCREENS
==================================================

1. LOGIN
2. DASHBOARD / COST USAGE
3. UNUSED SERVICES
4. LOW UTILIZATION
5. RECOMMENDATIONS
6. ACCOUNT

==================================================
DESIGN
==================================================

Create a modern premium FinOps SaaS interface.

The UI should feel:
- clean
- modern
- professional
- data-focused
- simple
- trustworthy
- enterprise-quality

Use a dark-first visual style:
- deep navy / charcoal background
- white/light-gray typography
- subtle cyan/blue accents
- AWS orange
- Azure cyan/green
- GCP purple
- green for savings
- amber for warnings
- red for critical issues

Use:
- rounded cards
- subtle borders
- soft shadows
- clean spacing
- modern typography
- polished charts
- subtle animations
- responsive layouts

Take inspiration from Linear, Vercel, Datadog and modern cloud dashboards, but create an original Cloud Advisor design.

Do NOT make it overly complicated or look like a generic admin dashboard.

==================================================
APPLICATION SHELL
==================================================

Create:
- collapsible left sidebar
- top navbar
- profile menu
- notifications
- cloud selector
- date selector
- refresh/sync button

Sidebar:

Dashboard
Cost Usage
Unused Service
Low Utilization
Recommendations
Account

Cloud selector:
AWS
Azure
GCP

The selected cloud should affect the dashboard data and styling.

==================================================
DASHBOARD / COST USAGE
==================================================

This is the primary page.

Header:
“AWS Cost Usage” / “Azure Cost Usage” / “GCP Cost Usage”

Controls:
Daily
Monthly
Custom Date Range

KPI cards:
- Total Cost
- Average Monthly Cost
- Service Count

Main visualization:
- cost trend over time
- service cost breakdown
- cost distribution

Below:
Service table with:
Service
Cost
Change
Trend

Use realistic demo data.

The dashboard should visually resemble the current existing Cloud Advisor dashboard, but significantly improve:
- spacing
- typography
- cards
- charts
- responsiveness
- visual hierarchy

==================================================
UNUSED SERVICES
==================================================

Create a simple but polished page.

Show:
- potentially unused services
- provider
- current cost
- last activity
- service name
- review status

Use cards or a table.

Clicking a service opens a detail drawer/modal showing:
- cost history
- activity information
- evidence
- recommendation

IMPORTANT:
Low cost does not automatically prove that a service is unused.

Use wording:
“Potentially Unused”
“Low Activity Detected”
“Review Recommended”

==================================================
LOW UTILIZATION
==================================================

Show resources that may be underutilized.

Display:
- resource
- provider
- service
- CPU utilization
- memory utilization
- cost
- estimated savings
- recommendation

Include:
- one useful utilization chart
- clean resource table
- filters

Keep this page simple and easy to understand.

==================================================
RECOMMENDATIONS
==================================================

Make this the most visually polished screen.

Each recommendation should show:

Recommendation title
Provider
Resource
Problem
Evidence
Potential Savings
Priority
Confidence

Example:

Right-size EC2 Instance

CPU: 4.8%
Memory: 11.3%
Monthly Cost: $112
Potential Savings: $67/month

Buttons:
View Details
Review

Recommendation detail should explain:
- why it was detected
- evidence
- cost impact
- suggested action

==================================================
ACCOUNT
==================================================

Create a simple modern profile page.

Show:
- avatar
- name
- email
- role
- default cloud
- theme preference

Cloud connections:
AWS
Azure
GCP

Show:
Connected
Disconnected
Error

Never expose passwords or secrets.

==================================================
LOGIN
==================================================

Modern minimal login screen.

Include:
- Cloud Advisor branding
- username/email
- password
- show/hide password
- remember me
- login
- forgot password

Tagline:

“Understand cloud spend. Detect waste. Optimize with confidence.”

==================================================
DATA / API
==================================================

Create a clean frontend architecture:

src/
  components/
  pages/
  api/
  services/
  mockData/
  config/
  hooks/
  utils/

Keep mock data separate from UI components.

Existing backend services:

Authentication: localhost:8000
AWS: localhost:5000
Azure: localhost:5001
Unused Services: localhost:5002
GCP: localhost:5005

Use centralized API configuration.

Do not scatter URLs throughout components.

If backend APIs are unavailable:
- use realistic demo data
- show “Using Demo Data”
- show “Last Synced”
- provide a retry option
- never crash the page

==================================================
UX REQUIREMENTS
==================================================

Include:
- loading skeletons
- empty states
- error states
- responsive layouts
- hover states
- polished chart tooltips
- sortable tables
- filters
- pagination
- accessible focus states
- tablet/mobile navigation

Make desktop the primary experience, but ensure the UI works properly on mobile.

==================================================
IMPORTANT
==================================================

Keep V1 intentionally simple.

DO NOT build:
- Rules Engine screens
- ML dashboards
- AI chatbot
- Findings Center
- Approval Center
- Reports
- Data Explorer
- complex enterprise administration

Those are future V2 features.

The goal is to create a polished V1 around the existing core functionality:

Cloud Selection
→ Cost Usage
→ Unused Services
→ Low Utilization
→ Recommendations
→ Account

FINAL GOAL:

Take the existing Cloud Advisor project and turn its simple functional frontend into a modern, premium, clean and responsive FinOps product.

Keep the functionality simple.
Make the UI exceptional.
Make the data realistic.
Make every screen feel finished.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/1ab3cc50-faff-4b5b-b40a-987ef2e1e82a).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
