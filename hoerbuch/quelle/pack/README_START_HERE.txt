THE HIGH-END WINGMEN — ELEVENLABS PREMIUM PRODUCTION PACK V2

This package replaces the old offline TTS workflow. It contains a rewritten, narration-ready audiobook manuscript with 33 tracks, a bilingual casting test, a pronunciation dictionary, an ElevenLabs Studio import file and an optional local API renderer.

FASTEST ROUTE — ELEVENLABS STUDIO
1. Create or open an ElevenLabs account.
2. In Studio, choose New audiobook.
3. Import 01_Studio_Import/High_End_Wingmen_Audiobook_Studio_Import_v2.docx.
4. Studio should detect the chapter headings automatically.
5. Open the Voice Library and filter: German, male, middle-aged, Narration or Conversational.
6. Test at least three voices with 03_Casting/01_Bilingual_Casting_Script.txt.
7. Use the same voice for German and English. Reject any voice with accent drift or clipped endings.
8. Model: Multilingual v2 for the full book. Use v3 only for isolated dialogue tracks if its performance is clearly better in your tests.
9. Upload 04_Pronunciation/wingman_pronunciation_aliases.pls in project settings.
10. Convert two complete chapters first: State & Flow and English Field Scripts. Only then convert the full project.

RECOMMENDED START SETTINGS
- Stability: 45 to 55 percent
- Similarity: 75 to 85 percent
- Style: 10 to 25 percent
- Speaker boost: on
- Do not maximize emotion. The target is premium conversational narration.

QUALITY GATE
- Natural German sentence endings
- English without strong accent drift
- Dialogue sounds spontaneous, not theatrical
- No table tags or bullet labels are spoken
- No robotic half-second gaps after every line
- Same loudness and identity across chapters

ALTERNATIVE — LOCAL API RENDERER
See 05_API_Renderer/README_API.txt. The renderer creates casting tests and then 33 separate MP3 chapters. The API key stays in an environment variable and is not stored in the package.
