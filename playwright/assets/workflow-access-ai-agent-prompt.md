
# Workflow Access Control – AI Agent Prompt

## Project Context
You are working inside an existing CMS/editor ecosystem used for journal production workflows.

This system supports multiple publishing clients and role-based workflows similar to a legacy implementation.

Legacy reference implementation location:

C:\_IMPACT\impact_tesing_jar_

The legacy system should be used only as **behavior reference**, not copied directly.

The goal is to **rebuild the workflow logic cleanly and modularly**.

---

# Supported Clients

PLOS  
LWW, AHA|NON-AHA Journals 
OUP  
MEDKNOW  
 BRILL

Client configuration affects:

- author verification
- editor access
- UI assets
- workflow routing

---

# Workflow Status Values

Possible file status:

active  
signoff  
deactive  
file_deleted  

Each status triggers specific behavior.

---

# ACTIVE STATUS

Condition

status === "active"

Workflow depends on:

- author count
- client

---

## Single Author Workflow

Condition

author_count === 1

### PLOS Client - least priroty 

Steps

1. Show dialog

Enter Author Access Code

2. Validate code

3. If valid

Redirect → Editor Page

---

### Non‑PLOS Clients

Clients:

OUP  
LWW AHA | NON-AHA 
MEDKNOW  


Skip access code.

Show confirmation dialog:

Allow access to editor?

Buttons

Accept  
Cancel

If Accept → open Editor Page

---

## Multiple Author Workflow

Condition

author_count > 1

Use

response.emailList

Steps

1. Prompt user

Which author is accessing this link?

2. Ask for email

Enter your email to verify access

3. Validate against email list

If valid → allow editor access

---

# Access Tracking

Store information

email  
access_time  
ip_address  
client  
article_id  
role  

Purpose

security  
audit trail  
workflow analytics  

---

# SIGNOFF STATUS

Condition

status === "signoff"

Editor access must be blocked.

Show alert

This article has been signed off.
You will be redirected to read‑only view.

Button

OK

Redirect → Read‑only page

---

## Special Rule for LWW

Condition

client === "LWW"
AND
role === "author"

Display

Author Sign Time

Example

Author Signed At:
2026‑03‑25 10:30 AM

Show on read‑only page header.

---

# DEACTIVE OR FILE_DELETED

Condition

status === "deactive"
OR
status === "file_deleted"

Show alert

This file is no longer active.
The article has been moved to archive mode.

Redirect → Archive Page

Editor access must be disabled.

---

# Client Asset Validation

Validate UI elements based on client.

Check

logos  
icons  
theme colors  
header graphics  

---

# Additional Content Validation

Verify the following content loads correctly

video tour  
FAQ  
help documentation  
support links  

Assets location

/assets/

Examples

/assets/videos/  
/assets/icons/  
/assets/help/  
/assets/faq/  

Assets must load dynamically based on

client  
workflow  
user role  

---

# Legacy Workflow Reference

Reference implementation

C:\_IMPACT\impact_tesing_jar_

The AI agent must:

1. Study the previous workflow behavior
2. Extract correct logic patterns
3. Avoid copying broken implementations
4. Rebuild workflow with modular architecture

Legacy workflow elements to analyze

workflow initialization  
author validation  
client routing  
status handling  
editor access control  

---

# Workflow Controller

Create controller

workflowAccessController.js

Responsibilities

detect file status  
identify client  
check author count  
verify user  
apply client rules  
route user to correct page  

---

# Possible Destinations

Editor Page  
Read‑Only Page  
Archive Page  
Verification Page  

---

# Validation Requirements

Before granting editor access validate

workflow status  
client rules  
author verification  
asset availability  

---

# Goal

Rebuild the workflow system so that it, based on analyses and requirments

matches legacy behavior  
fixes previous failures  
uses modular architecture  
is maintainable and scalable
