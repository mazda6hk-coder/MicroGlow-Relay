# MicroGlow Relay user guide

## Connecting

1. On the Models page, enter your provider endpoint and API key, then add models.
2. Exit the Codex desktop app and CLI normally. Turn on Relay, wait for the service to be ready, and follow the prompts to enable the Codex connection.
3. Restart Codex. For Claude Code, use its corresponding connection switch and follow the prompts.

Turning Relay off or exiting normally restores native Codex access. Minimizing to the tray does not exit the app; use Exit in the tray menu.

Exit Codex / Claude Code first, then exit Relay. Relay restores the connection settings before exiting. If restoration fails, Relay stays open and shows the reason. Resolve the issue and try exiting again.

## Models and sessions

- Choose a model within your Codex session. Set the default on the Models page, where you can add, edit, search and delete configurations and add multiple channels for one model.
- When a saved model name exactly matches a native Codex model name, that entry appears in the Codex model picker. For example, saving a configuration named `gpt-6-astra` makes that entry available. Removing the last configuration serving it removes the entry. Names without a matching configuration are not listed.
- A native entry forwarded through Relay to a third-party endpoint can continue the conversation, but encrypted reasoning content is removed. The third party receives reasoning summaries and text. Only OpenAI can read OpenAI's encrypted content. To retain the encrypted reasoning chain, use a channel pointing to `api.openai.com` with your own OpenAI key.
- Session continuity changes only the selected session's access configuration, without rewriting conversation history. Follow the prompts to exit Codex normally first.
- Both conversion directions use the same steps: exit the Codex desktop app and CLI, select the session and target, then apply. Codex does not need to be running or signed in, and Relay does not need to be on. Save a model configuration before converting to Relay access.
- Conversion back to official access first uses the newest eligible official session model, or that session's original official metadata backup if no reference is available. It stops if neither source is trustworthy.
- After conversion, turn Relay on before starting Codex for Relay access, or off before starting Codex for official access. Codex may still ask you to sign in to official services.

## Frequently asked questions

### No models?

A fresh installation has no preconfigured models. Add your own provider and models. Fetch available models supports multiple selections; each model is saved as a separate configuration.

### Requests fail?

Check the endpoint, API key, balance and model name. Do not include keys or conversation content in feedback.

### Where do Token statistics come from?

They use usage information in the original upstream response. Relay does not send extra requests for each place displaying the statistics.

### How do I use Trip Token A/B?

A and B are independent subtotals, each counting its selected scope from its own reset time. They continue across midnight and app restarts; only Reset on that subtotal clears it. Reset leaves today's totals and request logs unchanged and archives the old interval in Trip history. Use them for separate tasks and name them as needed. Failed requests still count as requests; Token totals use usage reported upstream.

### How do date filters work?

Choose a date and a day, week, month, quarter or year period to view the corresponding range. Error ratios use total requests in that range as the denominator.

### How does anonymous statistics consent work?

Neither consent option is preselected during installation. Choose to join or decline once to continue. This controls both local anonymous statistics and upload permission, without a second confirmation. Refusing does not affect installation or use; you can change your choice in Settings. Fresh silent installations default to off; silent upgrades preserve existing consent. Upload is attempted only on normal exit, with failures retried at the next exit. See the privacy policy for all fields and storage behavior.

### How do updates work?

With automatic checks enabled, Relay checks after startup and every 24 hours in the background. GitHub is the primary source and the official website is the fallback. New installers download automatically and are checked for size and SHA256 integrity. Click Install update in Settings to open the installer, and exit Relay normally before installing. Installers never run automatically. You can also use Check now for a manual check.

### Data and uninstalling

Settings shows the data directory. Uninstalling preserves user data. To remove it, exit Relay normally, back up anything you need, then remove that specific data directory. Do not delete the Codex directory.

## Contact

- Website: https://www.microglow.com.cn
- Product support: support@microglow.com.cn
- Privacy: privacy@microglow.com.cn
- Security reports: security@microglow.com.cn
