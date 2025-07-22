# (Un)Hinge(d) - An Unofficial API Client & Command Center for Hinge 🔓💀

I got bored on a Saturday night and my DMs were a barren wasteland. Four hours later, this repo existed. A day after that, it had a full GUI.

This is a fully `async`, typed, and unhinged Python client for the Hinge API, complete with a Streamlit command center. I reverse-engineered their private API because I was convinced my dating life could be optimized with a bit of code. Turns out, I was right.

### The WTF Moment: No SSL Certificate Pinning?!

Yeah, you read that right.

One of the biggest dating apps in 2025, handling millions of users' data, **has no SSL certificate pinning** on their main API.

I was geared up for a multi-day war with Frida, Objection, and a mountain of reverse-engineering tools. I was ready to hook into the app at runtime and surgically disable their security. It took me longer to write this README than it did to bypass their "security," because there was nothing to bypass. The front door was wide open. 💀

### The Strategic Advantage (aka The Unfair Advantage 😈)

Hinge's app is a slot machine. It feeds you one profile at a time, forcing you to waste your 8 daily likes on whoever the algorithm feels like showing you first. That's low-IQ gameplay.

This tool gives you two superpowers:

1.  **Full Deck Visibility:** It fetches your *entire* daily recommendation queue at once and displays it in a clean UI. You see all 30-50 potential matches upfront, letting you make high-IQ, strategic decisions with your limited likes instead of just swiping on the first person who doesn't have a fish pic.
2.  **Geo-Arbitrage Your Dating Life:** Got multiple accounts for different regions? Now you can manage them all from one place. Perfect for when you need to switch from the German dating pool to the US one where everyone is "Open Mindeu Do You Lobeu Alone?" (iykyk 😭).

### Disclaimer 🙏

This is for educational purposes only. I built this to see if I could, and because I was bored. Don't be a creep. Don't use this for malicious purposes. I am not responsible if you get banned, cursed, get a date with your cousin, or ghosted into oblivion. If Hinge sends a C&D, they should also send a job offer.

### Features 🔥

* ✨ **A Full-Blown Streamlit GUI:** No more cringe command-line stuff. This is a full command center to manage your entire dating operation.
* **Full Authentication Flow:** Handles the entire SMS OTP login process and saves your session so you don't get rate-limited into oblivion like I did.
* **Chat Credential Heist:** Automatically performs the handshake to get the Sendbird JWT and the infamous websocket `session-key`.
* **Harvest Profile Data:** Fetch full user profiles, including photos, prompts, and all the juicy metadata.
* **Automated Swiping:** Programmatically `skip` profiles that don't pass the vibe check.

### Project Status: Kinda Cooked, Kinda Working 👨‍🍳

As of right now, authentication, fetching profiles, and **skipping** works flawlessly.

The **like** functionality is being a little bitch and is currently broken. I'll fix it when the dopamine hits again. PRs are welcome if you're not a coward.

### Setup & Usage

You know the drill.

1.  Clone the repo.
2.  `pip install -r requirements.txt`
3.  Create a `.env` file and put your phone number(s) in it:
    ```
    HINGE_PHONE_NUMBER="+49123456789"
    ```
4.  Run the app:
    ```bash
    streamlit run app.py
    ```
5.  The app will handle the rest. Log in, view your queue, and start making better life decisions.

### To-Do (aka More Unhinged Ideas)

  * [ ] **The "Anti-Ghosting" CRM:** A full dashboard to track your dating funnel.
  * [ ] **The Rizzler Agent™:** An AI that uses conversation history to generate replies in your own voice.
  * [ ] **The "Type Detector" ML Model:** Integrate the bot's brain to automate swipes based on your specific, hyper-niche aesthetic preferences.

Go break some shit. Or get a date. Whatever.