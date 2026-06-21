---
name: Epicurean Standard
colors:
  surface: '#fbf9f8'
  surface-dim: '#dbdad9'
  surface-bright: '#fbf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3f3'
  surface-container: '#efeded'
  surface-container-high: '#e9e8e7'
  surface-container-highest: '#e4e2e2'
  on-surface: '#1b1c1c'
  on-surface-variant: '#5b403f'
  inverse-surface: '#303031'
  inverse-on-surface: '#f2f0f0'
  outline: '#8f6f6e'
  outline-variant: '#e4bebc'
  surface-tint: '#bb162c'
  primary: '#b7122a'
  on-primary: '#ffffff'
  primary-container: '#db313f'
  on-primary-container: '#fffbff'
  inverse-primary: '#ffb3b1'
  secondary: '#5f5e5e'
  on-secondary: '#ffffff'
  secondary-container: '#e2dfde'
  on-secondary-container: '#636262'
  tertiary: '#5b5c5c'
  on-tertiary: '#ffffff'
  tertiary-container: '#737575'
  on-tertiary-container: '#fcfcfc'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdad8'
  primary-fixed-dim: '#ffb3b1'
  on-primary-fixed: '#410007'
  on-primary-fixed-variant: '#92001c'
  secondary-fixed: '#e5e2e1'
  secondary-fixed-dim: '#c8c6c5'
  on-secondary-fixed: '#1b1b1b'
  on-secondary-fixed-variant: '#474746'
  tertiary-fixed: '#e2e2e2'
  tertiary-fixed-dim: '#c6c6c7'
  on-tertiary-fixed: '#1a1c1c'
  on-tertiary-fixed-variant: '#454747'
  background: '#fbf9f8'
  on-background: '#1b1c1c'
  surface-variant: '#e4e2e2'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '800'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  container-max: 1200px
  edge-margin: 32px
  gutter: 24px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 24px
  section-gap: 48px
---

## Brand & Style
The design system is engineered for a premium, high-utility restaurant discovery experience. It balances the urgency of hunger with the sophistication of culinary exploration. The personality is professional, authoritative, and vibrant, positioning the app as a trusted curator rather than a mere directory.

The aesthetic follows a **Corporate Modern** approach with high-polish finishing. It utilizes a clean, high-contrast interface that prioritizes food photography and data clarity. The emotional response should be one of reliability and appetite, achieved through generous whitespace, crisp iconography, and a signature warm red focal point.

## Colors
The palette is anchored by a high-energy **Warm Red (#E23744)**, used strategically for primary actions and branding moments to stimulate appetite and drive conversions. The foundation is a stark **White (#FFFFFF)** for maximum legibility, paired with **Light Gray (#F8F8F8)** to define content containers and secondary panels.

Typography and iconography use **Dark (#1C1C1C)** for deep contrast. Specialized tokens are included for hierarchical rank badges: Gold for top-tier selections, Silver for runners-up, and Bronze for third-place highlights. Ratings should utilize a green-to-yellow scale to provide instant qualitative feedback.

## Typography
This design system relies exclusively on **Inter** to maintain a systematic, neutral, and highly readable interface. The type scale is optimized for information density, using weight shifts (Bold and SemiBold) rather than excessive size changes to denote hierarchy.

Display and Headline styles feature tighter letter-spacing to appear more cohesive at large scales. Body text is prioritized for legibility with a comfortable 1.5x line height. Labels use an uppercase treatment for clear categorization of meta-data like cuisine types or price brackets.

## Layout & Spacing
The layout follows a **Fixed Grid** philosophy for desktop, centering content within a 1200px max-width container to ensure focus. A 12-column system is used with a standard 24px gutter. 

Spacing is intentionally "generous" to avoid the cluttered feel of traditional directories. Vertical rhythm is maintained through increments of 8px. Large sections (e.g., "Popular Localities" vs "Collections") are separated by 48px to 64px gaps to allow the UI to breathe. On mobile, margins reduce to 16px, and the grid collapses to a single column for cards.

## Elevation & Depth
Depth is created using **Ambient Shadows** and **Tonal Layers**. 
- **Level 0 (Base):** White (#FFFFFF) background.
- **Level 1 (Sub-surface):** Light Gray (#F8F8F8) used for full-width sections or background "wells" behind cards.
- **Level 2 (Raised):** White cards with a very soft, diffused shadow (`0px 4px 12px rgba(28, 28, 28, 0.08)`). This is the standard for restaurant tiles.
- **Level 3 (Interactive):** Upon hover, cards should lift slightly (`0px 8px 24px rgba(28, 28, 28, 0.12)`) to provide tactile feedback.
- **Level 4 (Overlays):** Modals and dropdowns use a crisp border (1px #E8E8E8) combined with a deep shadow to separate from the main interface.

## Shapes
The design system uses a **Rounded** shape language to feel approachable and modern. 
- **Standard (8px):** Primary buttons, input fields, and restaurant cards.
- **Large (16px):** Featured collection banners and modal containers.
- **Pill (100px):** Search bars, filter chips, and category tags to distinguish them from actionable buttons.
- **Badge (4px):** Rating boxes and rank badges, using sharper corners to imply a "stamp" of quality.

## Components
- **Buttons:** Primary buttons are Solid Warm Red with white text. Secondary buttons use a 1px border of the Primary color or Neutral Gray.
- **Cards:** Restaurant cards feature a fixed-aspect-ratio image (16:9) at the top, followed by a padded content area with the restaurant name in Headline-SM and the rating badge positioned at the top right.
- **Rating Badges:** Small rectangles with a color background (Rating-High for 4.0+, Rating-Mid for 3.0+).
- **Rank Badges:** Circular or shield-shaped icons with a subtle metallic gradient (Gold, Silver, Bronze) and a white number inside, placed on the top-left corner of cards.
- **Filter Chips:** Pill-shaped, White background with 1px Gray border. When active, they transition to a light Red background with a Red border.
- **Input Fields:** Large, 48px-56px height for the primary search bar. It should include a location pin icon and a search magnifying glass icon for clear functional zones.
- **Lists:** Menu items or search results should use a horizontal layout with a small thumbnail (80x80px) and bottom-border dividers for clean separation.