# User Guide: Network Device Monitor

## Add a device
1. In **Add a device**, enter a **Name** (for example "Office router"), a **Host** (a website name like `example.com` or an IPv4 address) and a **Port** (for example `443` for websites).
2. Select **Start monitoring**. The first check runs straight away.

## Read the dashboard
- The cards at the top show the number of devices, how many are **Up** and how many are **Down**.
- Each device card shows its status pill, host and port, the latest response time and when it was last checked.
- The page refreshes itself every 10 seconds, and the server checks each device every 30 seconds.

## Check history
Select **History** on a device. Each row shows a coloured dot (green up, red down), the time, a bar for the response time (longer means slower) and the milliseconds.

## Alerts
**Recent alerts** shows the newest 30 alerts. A red alert means a device went down (with the reason). A green alert means it recovered.

## Other buttons
- **Check now** runs a check immediately.
- **Remove** stops monitoring the device and deletes its history.

## Troubleshooting
| Problem | What to do |
| --- | --- |
| "Host name could not be resolved" | Check the spelling of the host. |
| "Connection timed out" | The device did not answer within 2 seconds. It may be down or blocking that port. |
| "Private and local addresses are not allowed" | The public demo blocks internal addresses for safety. Run the app locally to monitor your own network. |
