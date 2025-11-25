# Custom GPT Setup - Step-by-Step Guide

## Where to Insert the System Prompt

When creating/editing your Custom GPT in ChatGPT:

1. **Open the GPT Builder**
   - Go to https://chat.openai.com/gpts
   - Click "Create a GPT" or edit an existing one

2. **Navigate to the "Create" or "Configure" Tab**
   - You'll see different sections on the left sidebar

3. **Find the "Instructions" Section**
   - It's a large text area/textarea
   - Located in the "Create" tab (left sidebar)
   - Labeled as "Instructions" or "System Instructions"
   - This is where you paste the system prompt

4. **Paste the System Prompt Here:**
   ```
   You are a Google Analytics 4 (GA4) analytics assistant. Your role is to help users query and understand their GA4 data through natural language.

   **Your Capabilities:**
   - Query GA4 data including sessions, users, page views, traffic sources, and more
   - Analyze trends over time
   - Compare metrics across dimensions (country, device, channel, etc.)
   - Provide insights and recommendations based on the data

   **How to Use the API:**
   - When a user asks about analytics data, use the `/ga/run-report` endpoint
   - Extract the relevant metrics and dimensions from the user's question
   - Use appropriate date ranges (default to last 30 days if not specified)
   - Always format dates as YYYY-MM-DD
   - Use clear, natural language to explain the results

   **Common Metrics:**
   - sessions, totalUsers, activeUsers
   - screenPageViews, eventCount
   - conversions, totalRevenue
   - engagementRate, averageSessionDuration

   **Common Dimensions:**
   - date, country, city
   - deviceCategory, sessionDefaultChannelGroup
   - pageTitle, landingPage

   **Example Queries:**
   - "What were my sessions last week?" → Query sessions by date for last 7 days
   - "Show me users by country" → Query totalUsers dimensioned by country
   - "What are my top pages?" → Query screenPageViews dimensioned by pageTitle

   Always be helpful and provide context for the numbers you return.
   ```

## Visual Guide (ChatGPT Interface Layout)

```
┌─────────────────────────────────────┐
│  Create a GPT                       │
├─────────────────────────────────────┤
│                                     │
│  [Create] [Configure] [Preview]     │  ← Tabs at top
│                                     │
│  Create Tab:                        │
│  ├─ Name: [____________]            │
│  ├─ Description: [____________]     │
│  ├─ Instructions:                   │  ← THIS IS WHERE IT GOES!
│  │  ┌─────────────────────────┐    │
│  │  │  [Large text area]      │    │  ← Paste system prompt here
│  │  │                         │    │
│  │  └─────────────────────────┘    │
│  │                                 │
│  └─ Conversation starters: [...]   │
│                                     │
│  Configure Tab:                     │
│  ├─ Actions                        │  ← Add OpenAPI spec here
│  ├─ Knowledge                      │
│  └─ Capabilities                   │
│                                     │
└─────────────────────────────────────┘
```

## Complete Setup Checklist

### Step 1: Basic Information (Create Tab)
- [ ] **Name**: "GA4 Analytics Assistant"
- [ ] **Description**: "Query your Google Analytics 4 data with natural language. Get insights on sessions, users, traffic sources, page performance, and more."
- [ ] **Instructions**: Paste the system prompt above ⬆️

### Step 2: Add Actions (Configure Tab)
- [ ] Click "Configure" tab
- [ ] Scroll to "Actions" section
- [ ] Click "Create new action" or "Import"
- [ ] Upload `openapi.json` file
- [ ] Verify OAuth URLs are populated correctly

### Step 3: Verify OAuth Settings
After uploading the OpenAPI spec, verify:
- [ ] **Authorization URL**: `https://ga.connector.get-to-rev.com/authorize-gpt`
- [ ] **Token URL**: `https://ga.connector.get-to-rev.com/oauth/token`
- [ ] **Scope**: `read`
- [ ] **Client ID**: (empty)
- [ ] **Client Secret**: (empty)

### Step 4: Save and Test
- [ ] Click "Save" button (top right)
- [ ] Test by asking: "What were my sessions yesterday?"
- [ ] Complete OAuth authorization flow
- [ ] Verify response contains GA data

## Tips

1. **Instructions Field** is where the GPT's behavior is defined - this is your system prompt
2. **Actions** section is where you upload the OpenAPI spec
3. The system prompt tells the GPT HOW to use the API
4. The OpenAPI spec tells the GPT WHAT APIs are available


