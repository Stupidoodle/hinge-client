# (Un)Hinge(d) - An Unofficial API Client for Hinge 🔓💀

I got bored on a Saturday night and my DMs were a barren wasteland. Four hours later, this repo exists.

This is a fully `async`, typed, and unhinged Python client for the Hinge API. I reverse-engineered their private API because I was convinced my dating life could be optimized with a bit of code. Turns out, I was right.

### The WTF Moment: No SSL Certificate Pinning?!

Yeah, you read that right.

One of the biggest dating apps in 2025, handling millions of users' data, **has no SSL certificate pinning** on their main API.

I was geared up for a multi-day war with Frida, Objection, and a mountain of reverse-engineering tools. I was ready to hook into the app at runtime and surgically disable their security. It took me longer to write this README than it did to bypass their "security," because there was nothing to bypass. The front door was wide open. 💀

### Disclaimer 🙏

This is for educational purposes only. I built this to see if I could, and because I was bored. Don't be a creep. Don't use this for malicious purposes. I am not responsible if you get banned, cursed, get a date with your cousin, or ghosted into oblivion. If Hinge sends a C&D, they should also send a job offer.

### Features 🔥

* **Full Authentication Flow:** Handles the entire SMS OTP login process.
* **Chat Credential Heist:** Automatically performs the handshake to get the Sendbird JWT and the infamous websocket `session-key`.
* **Get Recommendations:** Pull down the main feed of potential matches.
* **Harvest Profile Data:** Fetch full user profiles, including photos, prompts, and all the juicy metadata.
* **Automated Swiping:** Programmatically `like` or `skip` profiles. Yes, it works on photos and prompts.

### The Heist Plan: How Auth Works

The authentication is a beautiful, convoluted mess that I've fully automated.

1.  **Device Registration (`/identity/install`):** Your client pretends to be a fresh install of the app.
2.  **Hinge Master Key (`/auth/sms/v2`):** You submit your OTP and get back the main `Bearer` token for Hinge's API.
3.  **The Sendbird Bridge (`/message/authenticate`):** You trade your Hinge token for a temporary Sendbird JWT.
4.  **The Websocket Key Heist:** You connect to the Sendbird websocket with the JWT, and the server just hands you the `session-key` in the initial `LOGI` message. No cap.

### Setup & Usage

You know the drill.

1.  Clone the repo.
2.  `pip install -r requirements.txt`
3.  Create a `.env` file and put your phone number in it:
    ```
    HINGE_PHONE_NUMBER="+49123456789"
    ```
4.  Run `hinge_client.py`. Enter the OTP when it asks.
5.  Watch the magic happen. Or watch it crash. I wrote this in 4 hours, what do you expect?

### To-Do (aka More Unhinged Ideas)

* [ ] **The "Anti-Ghosting" CRM:** A full dashboard to track your dating funnel.
* [ ] **The Rizzler Agent™:** An AI that uses conversation history to generate replies in your own voice.
* [ ] **The "Type Detector" ML Model:** Integrate the bot's brain to automate swipes based on your specific, hyper-niche aesthetic preferences.

Go break some shit. Or get a date. Whatever.