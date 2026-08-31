"""Scene planner for short educational videos."""

SCENES = [
    {
        "id": 1,
        "lyrics": "أَدَّبَنِي الإِسْلَامُ الأَعْظَمْ\nمِنْ هَدْيِ رَسُولِي أَتَعَلَّمْ",
        "prompt": "Warm 3D animated cartoon majlis. A cheerful young Arab boy in a white thobe sits naturally among a circle of family and friends, listening respectfully to an older man. Friendly educational children's animation, expressive faces, natural interaction, vertical 9:16."
    },
    {
        "id": 2,
        "lyrics": "لَا أَرْفَعُ صَوْتًا فِي الْمَجْلِسْ",
        "prompt": "Same 3D cartoon boy seated inside the majlis circle. He speaks calmly and softly, then makes a gentle no gesture to show that he should not raise his voice. Other people remain naturally engaged. Vertical 9:16."
    },
    {
        "id": 3,
        "lyrics": "لَا أَلْمِزُ أَحَدًا أَوْ أَهْمِسْ",
        "prompt": "Same boy among the group notices two children whispering to each other. He gently signals no with his hand, showing good manners without anger. Warm playful 3D children's cartoon, natural interaction, vertical 9:16."
    },
    {
        "id": 4,
        "lyrics": "لَسْتُ أُقَاطِعُ مَنْ يَتَكَلَّمْ",
        "prompt": "Same majlis. Another person is speaking while the boy patiently waits for his turn, listening attentively and smiling. Clear visual storytelling about not interrupting, 3D animated children's movie style, vertical 9:16."
    },
    {
        "id": 5,
        "lyrics": "أُحْسِنُ حِينَ أَقُولُ كَلَامَا\nلَا مُغْتَابًا أَوْ نَمَّامَا",
        "prompt": "Same boy speaks kindly to the people around him with a friendly smile. The group reacts positively. He makes a gentle no gesture when gossiping is suggested. Warm 3D cartoon storytelling for children, vertical 9:16."
    },
    {
        "id": 6,
        "lyrics": "وَإِذَا مَا خَاطَبَنِي جَاهِلْ\nوَ أَطَالَ لِسَانًا بِالْبَاطِلْ",
        "prompt": "Same majlis. One person speaks rudely and gestures too much, while the boy remains composed, patient and peaceful. No violence or fear, humorous child-friendly 3D cartoon expression, vertical 9:16."
    },
    {
        "id": 7,
        "lyrics": "أَصْبِرُ ثُمَّ أَقُولُ: سَلَامَا",
        "prompt": "Same boy stays calm, smiles, raises his hand politely in farewell and peacefully says goodbye. The scene ends warmly with the group smiling, memorable uplifting 3D children's animation ending, vertical 9:16."
    },
]


def get_scenes():
    return SCENES