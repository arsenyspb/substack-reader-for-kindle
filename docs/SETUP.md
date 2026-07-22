# 🚀 Setup Instructions

This guide will walk you through the three main steps required to get your own Substack-to-Kindle pipeline running.

## 1. Gmail Configuration
*   **Enable 2-Step Verification:** Required for App Passwords. [Instructions here](https://support.google.com/accounts/answer/185839).
*   **Generate an App Password:** [Create one here](https://myaccount.google.com/apppasswords) specifically for "Mail" (select "Other" for device name and call it `Substack RFK`). Save this password.
*   **Create Labels:** In Gmail, create two labels: `Substack-Kindle` and `Substack-Kindle-Processed`.
*   **Set up a Filter:** 
    *   **Direct Newsletters:** Create a filter for `from:substack.com` -> "Apply label: `Substack-Kindle`" and "Skip the Inbox".
    *   **Forwarded Newsletters:** If you forward emails from another account, create a filter for `from:your-main-email@gmail.com` and `Has the words: substack.com` -> "Apply label: `Substack-Kindle`".

## 2. Google Sheet Setup
*   **Copy the Template:** [Click here to copy the template sheet directly to your Google Drive](https://docs.google.com/spreadsheets/d/1kJaFn914UtyzH0sDeVDlxFKmetmpXgec1vLhaKVpp84/copy).
*   **Prepare the Layout:**
    1.  Ensure Row 1 contains the instruction text (you can merge cells across A1-E1).
    2.  Ensure Row 2 contains the headers: `Status`, `Subject`, `Sender`, `Date`, `Message-ID`.
*   **Set the API Secret:**
    1.  Go to `Extensions -> Apps Script`.
    2.  Delete all code and paste the content from `templates/Code.gs`.
    3.  Click the **Gear Icon** (Project Settings) on the left sidebar.
    4.  Scroll down to **Script Properties** -> **Add script property**.
    5.  Property: `WEB_APP_SECRET` | Value: *Any random secure string*. **Save this value.**
*   **Deploy as Web App:**
    1.  Click the blue **Deploy** button -> **New Deployment**.
    2.  Click the "gear" ⚙️ icon next to "Select type" and choose **Web app**.
    3.  **Description:** Type `Substack RFK API`.
    4.  **Execute as:** Select `Me (<your-email>)`. *(This allows the script to edit your sheet).*
    5.  **Who has access:** Select `Anyone`.
        > 🛡️ **Security Note:** Selecting "Anyone" sounds scary, but it is required so GitHub Actions can talk to it. Your sheet is **safe** because every request is protected by the `WEB_APP_SECRET` you created in the previous step. Without that exact password, the script rejects all connections.
    6.  Click **Deploy**. (If prompted, click **Authorize Access** -> choose your account -> **Advanced** -> **Go to Project (unsafe)**).
    7.  **Copy the "Web app URL"** shown in the final popup (it should end in `/exec`). Do **NOT** copy the Deployment ID or the URL from your browser's address bar.

## 3. GitHub Configuration
*   **Fork this Repository:** Click the "Fork" button at the top of this page. Or, if you prefer the command line, use the [GitHub CLI](https://cli.github.com/):
    ```bash
    gh repo fork arsenyspb/substack-reader-for-kindle --clone
    ```
*   **Automated Setup (Recommended):**
    If you have the [GitHub CLI](https://cli.github.com/) installed, simply run this command from the project root and follow the prompts:
    ```bash
    ./scripts/setup_github.sh
    ```
*   **Manual Setup:**
    Go to `Settings -> Secrets and variables -> Actions` in your fork and add the following configuration values under **Repository secrets** (do **not** add them as Variables, otherwise they will be exposed in workflow logs):
    *   `GMAIL_USER`: Your Gmail address.
    *   `GMAIL_APP_PASSWORD`: The App Password from Step 1.
    *   `KINDLE_EMAIL`: Your "Send to Kindle" email address.
    *   `WEB_APP_URL`: The URL from Step 2.
    *   `WEB_APP_SECRET`: The secret string from Step 2.
    *   `ALLOWLISTED_SENDERS` (Optional): Comma-separated list of emails to process.
    *   `AUTO_APPROVE` (Optional): Set to `true` to bypass the manual Triage phase. Emails will be automatically marked as `APPROVED` upon sync. *Note: This is not recommended as it bypasses the spam protection layer of the triage sheet, but the items will still be visible in the Google Sheet.*

    > **Note:** You must add your `GMAIL_USER` email address to your **Approved Personal Document E-mail List** in your Amazon account settings. [Configure it here](https://www.amazon.com/hz/mycd/preferences/myx#/home/settings/payment).
