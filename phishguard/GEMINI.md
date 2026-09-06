# Frontend Design Guidelines & Aesthetic Rules

When working on the frontend of PhishGuard, you must strictly adhere to the following design constraints:

1. **Aesthetic Identity**: The UI must maintain a "deep dark hacker" aesthetic.
2. **Color Palette**: 
   - Use a very dark base background (e.g., `#050508`).
   - Use vivid neon accents, specifically Neon Cyan (`#00e5ff`) for primary interactive elements.
   - Use Neon Crimson (`#ff4d4f`), Neon Amber (`#ffa940`), and Neon Green (`#39ff14`) sparingly for risk levels or statuses.
3. **Glassmorphism**: Use crisp glassmorphism (translucent backgrounds with backdrop-filter blur and subtle neon borders) for cards and panels.
4. **No Light Themes**: Do not implement or default to light mode themes or overpowering bright/radial gradients that wash out the page.
5. **Animations**: Keep animations slick but constrained (e.g., scan-lines, subtle pulses, ease-out arc fills). Ensure a reduced-motion toggle exists if adding heavy animations.
