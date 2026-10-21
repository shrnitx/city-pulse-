# DRCivic marketing site

A self-contained responsive landing page for DRCivic, built with semantic HTML, CSS and lightweight JavaScript. It is intentionally isolated from the production React frontend under `frontend/`.

## Deploy on Vercel

Create a Vercel project linked to `shrnitx/city-pulse-` and set **Root Directory** to `drcivic-site`. No build command or framework preset is required; this is a static HTML site.

## App links

The landing page's “Open DRCivic” links point to the currently configured Vercel web-app domain. The source repository does not currently contain a published Android APK or release asset. When a signed APK or Play Store listing is available, update the call-to-action in `index.html` rather than presenting the source repository as an app download.

## Edit the visual system

Colors, typography, layouts and animations are defined near the top of `index.html` in the `:root` variables and embedded styles. The dashboard illustration uses illustrative sample values and is explicitly labeled as sample data.
