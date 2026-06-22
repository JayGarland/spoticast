# AI Companion Personalization and Trust  
AI companions must balance **personalization** with user trust. Research shows that over-personalization—when an AI mentions private details or uses them oddly—can trigger an “uncanny valley” effect of linguistic trust. As Jefferson Barlew notes, an AI that suddenly brings up unsought personal details feels like a *surveillance agent*, not a friendly helper. Conversely, transparency and user control are key trust factors. Responsible design guidelines emphasize informing users about personalization and giving them opt-out or deletion controls. In practice, popular services already personalize aggressively but carefully. For example, Spotify’s new AI DJ marketings itself as “a personalized AI guide that **knows you and your music taste so well**” and provides commentary on songs “we think you’ll like”. Yet even there, the actual commentary focuses on music and genres, not on the user’s personal life. These examples show personalization can enhance engagement if it stays on-topic (music) and respects the user’s privacy (no private details).

# Industry Voice-UX Patterns  
Voice assistants and radio hosts use personalization sparingly.  Many smart-speaker UIs allow addressing the user by name, but studies find users quickly notice and react if the assistant uses personal context incorrectly.  Design best-practices suggest mentioning user-related info only when it’s clearly relevant. In radio and streaming, personalized playlists (e.g. Pandora/Spotify “Your Daily Mix”) are common, but on-air hosts rarely say things like “John, this one’s for you.” Instead, they might say “For anyone who loves late-night chill” (third-person descriptor) or keep it generic. The **Spotify AI DJ** itself is an instructive case: it’s explicitly personalized (“curated lineup for *you*”), yet its commentary is about the music (“about tracks and artists we think you’ll like”) rather than calling out the listener by name. This implies a middle ground – personalization framed as insight into *music tastes*, not personal data.

# Stance Options (A, B, C) vs. Constraints  
We compare the three approaches against the owner’s **hard constraints** (no private inventory, no cross-cast memory, not overly timid, commentary matching the playlist):

- **A: Overhear (current)** – *Hosts never mention the listener.* Everything is generic to the music.  
  - *Pros:* Fully avoids privacy creep (“surveillance agent” risk). Satisfies “descriptor, never inventory” and no-history constraints by design. Very safe.  
  - *Cons:* Can feel cold or generic, lacking warmth/personal connection. Might frustrate users who expect some nod to their taste. Could violate “not timid” if it becomes boring or repetitive.  

- **B: Acknowledge (third-person)** – *Hosts never say “you,” but they use mood descriptors that subtly reflect the listener’s taste.* (Example: “This set feels built for someone who loves the quieter side of things.”)  
  - *Pros:* Adds warmth and personalization without breaching privacy. It obeys the “descriptor, never inventory” rule by using abstract mood/genre terms, not actual artist names. This follows conversational relevance: it comments on vibe. It avoids direct address, so it’s less creepy.  
  - *Cons:* Must be careful the descriptor fits the playlist (constraint: “playlist conveys vibe”). If the hosts guess wrong (“If you’re into the quiet side, this track’s for you,” but the playlist is heavy metal) it breaks trust. Also must avoid any phrasing that sounds like “you have these exact preferences.” Otherwise it stays within constraints.  

- **C: Address You Directly** – *Hosts speak to “you” (still only using descriptors, no factual data). Example: “If you’re in the mood for something slower tonight, this one fits.”*  
  - *Pros:* Most personal and engaging. Feels like a real companion speaking to you. Can clearly guide the experience.  
  - *Cons:* Highest privacy risk. Even benign second-person can feel like it’s watching you. As Barlew’s “mob boss implicature” suggests, hearing “you” can prompt listeners to wonder what the AI really knows about them. Hard constraint checks: must NEVER slip into actual history or data, only mood hints. Risk: any misstep (e.g. “Last time you...” or “I know you”) would feel invasive. Also requires ensuring *all* content aligns with playlist (no mismatches).  

Each stance must respect: (1) **Descriptor-only**, not naming personal data; (2) **No history** between casts (fresh each time); (3) not be overly cautious/robotic; (4) commentary must match the music mood (honor the playlist’s vibe).

**Related research:** A Spotify case study warned of the “personalization paradox” – when an AI is *too* human-like or personal, users feel alienated. Users also expect clear value: e.g., Spotify’s DJ improves as you “tell it what you like” (transparency of feedback), reinforcing control. Trust studies support moderate personalization with opt-in control, not surprise details.

# Recommendation and Rollout Plan  
We recommend **Option B (“Acknowledge taste, not you”) as the default**. In practice, hosts would say things like “This next track should suit someone who likes a mellow vibe,” or “Built for those at the quieter end of the spectrum.” These lines acknowledge the inferred *style* of the listener (“quiet vibe”) without using “you” or listing personal data. This balances warmth and privacy. It fulfills the owner’s desire for “tasteful a bit” personalization and obeys the strict no-data guardrails.  

*Example host lines:*  
- **A (Overhear):** “That reverb tail is pure late-’90s Warp Records style.” (no mention of listener)  
- **B (Acknowledge):** “This set feels just right for someone who digs the calmer, ambient side of things.” (third-person, descriptor)  
- **C (Address):** “Looking to wind down tonight? This next song should fit the bill.” (direct “you”)

We **do NOT** recommend exposing modes to the user immediately (since that complicates the interface). Instead, implement B as the sole mode for now, with A and C remaining off by default. (Future: allow power-users to switch modes “Radio” vs “Companion” after more testing.) 

**Rollout:** Update the prompt so hosts use third-person descriptors. For example, change from “Now we play some ambient tracks” (A) to something like “We’ve got a set lined up for anyone who loves ambient, mellow sounds.” Ensure extensive testing to catch any accidental personal references. As the owner cautioned, this is a key “soul” decision – we’ll mark it as a checkpoint, get stakeholder sign-off, then deploy the change. 

**Sources:** UX and trust research indicate that subtle personalization (descriptors, no data) is acceptable, whereas overt personal address can trigger creepiness. Industry examples (e.g. Spotify’s AI DJ) likewise personalize music selection but avoid calling out individual user details. 

