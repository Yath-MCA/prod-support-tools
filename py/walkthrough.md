# CMS Editor Page Layout Implementation

The new Editor Page Layout has been successfully implemented using React, Tailwind CSS, and Lucide icons according to the specifications.

## What was Changed

1. **Role-Based Permissions**
   - Created [src/config/permissions.js](file:///c:/_IMPACT/tomcat/webapps/impact_vite/src/config/permissions.js) with `config` containing `type` and `userRole`.
   - Mapped `download`, `proofPDF`, `ceTrack`, `generateTrack`, and `finalize` actions based on `viewer`, `editor`, and `admin` roles.

2. **Components Added**
   - [SharedMiddleColumn](file:///c:/_IMPACT/tomcat/webapps/impact_vite/src/components/editor/SharedMiddleColumn.jsx#4-67): A reusable middle section component with Outline, Primary and Ghost buttons, dividers, and a dynamic Online/Offline toggle with pulsing animations.
   - [Navbar1](file:///c:/_IMPACT/tomcat/webapps/impact_vite/src/components/editor/Navbar1.jsx#6-92): The top navbar containing the PDF Action Buttons linked to user permissions, the shared middle column, and utility controls.
   - [Navbar2](file:///c:/_IMPACT/tomcat/webapps/impact_vite/src/components/editor/Navbar2.jsx#7-70): The secondary navbar displaying the `config.type` driven "Journal/Article" metadata alongside TOC and Thumbnail toggles, as well as the shared middle column.

3. **EditorPage Layout Refactor**
   - Refactored [src/pages/EditorPage.jsx](file:///c:/_IMPACT/tomcat/webapps/impact_vite/src/pages/EditorPage.jsx) into a dark-themed `h-screen`, `flex-col` layout.
   - Removed legacy header, footer, and toolbar components.
   - Inserted [Navbar1](file:///c:/_IMPACT/tomcat/webapps/impact_vite/src/components/editor/Navbar1.jsx#6-92) and [Navbar2](file:///c:/_IMPACT/tomcat/webapps/impact_vite/src/components/editor/Navbar2.jsx#7-70) at the top.
   - Designed a responsive conditionally rendered [SharedMiddleColumn](file:///c:/_IMPACT/tomcat/webapps/impact_vite/src/components/editor/SharedMiddleColumn.jsx#4-67) below [Navbar2](file:///c:/_IMPACT/tomcat/webapps/impact_vite/src/components/editor/Navbar2.jsx#7-70) exclusively for `<md` screens.
   - Structured the main body area into a 3-panel `flex-1` layout:
     - **Left Panel (TOC):** Conditionally rendered, fixed width `w-56`, tied to [Navbar2](file:///c:/_IMPACT/tomcat/webapps/impact_vite/src/components/editor/Navbar2.jsx#7-70) toggle.
     - **Center Panel (Editor):** Centered `CKEditor` document card container that takes up remaining space and scrolls independently.
     - **Right Panel (Thumbnails):** Conditionally rendered, fixed width `w-[112px]`, tied to [Navbar2](file:///c:/_IMPACT/tomcat/webapps/impact_vite/src/components/editor/Navbar2.jsx#7-70) toggle.

## Verification

- The project builds successfully (`npm run build`).
- The components are cleanly modularized.
- Responsive breakpoints (`md:hidden`, `hidden sm:inline`) are applied to handle the `<md` breakpoint criteria and text label hiding.
- The `CKEditor` retains its functionality while sitting in the new `max-w-4xl` document container.
