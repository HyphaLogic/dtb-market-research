# DTB Design Archetype Grammar (Brock, review rounds 2-4)
Compositional slots rather than single categories:
- **Frame** (yes / no / reverse) - black structural frame (waistband + side/hem lines) containing artwork
- **Base** - solid | gradient | pattern | energy-element | graffiti
- **Accent** - block panel(s) | trim/piping | graphic/silhouette | bands | none

Ground-truth examples: "Frame + Pattern", "Color Gradient + Block", "Energy + Solid",
"Solid + Block Panels", "Pattern + Graffiti", "Reverse Frame".
Machine labels should emit all three slots. Waistband recorded separately (black ~80% convention).
