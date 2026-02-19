# Zotero API Configuration Troubleshooting

## Problem: 404 Error

```
Response [https://api.zotero.org/group/2810748/collections/U4SW8TCS/items?...]
  Status: 404
Error: Zotero API error: 404
```

## Causes and Solutions

### Cause 1: Wrong Endpoint Format (Most Likely)

The Zotero API expects items from `/collections/{key}/items/top` but the script was calling `/collections/{key}/items`.

**Solution:** Added `/top` to the URL in the updated script.

```r
# OLD (WRONG):
"https://api.zotero.org/{type}/{id}/collections/{key}/items"

# NEW (CORRECT):
"https://api.zotero.org/{type}/{id}/collections/{key}/items/top"
```

### Cause 2: Wrong Collection ID Format

The Collection ID might need to be in a different format.

**Solution:** Run the configuration helper to find the correct collection ID:

```bash
Rscript zotero_config_helper.R
```

This will:
1. List all your groups
2. List all collections in each group
3. Try fetching items to verify the correct IDs
4. Print recommended configuration

### Cause 3: Collection is Empty

The target collection contains no items.

**Solution:** Check Zotero web interface to verify items are in the collection.

---

## How to Find Correct Configuration

### Step 1: Run the Configuration Helper

```bash
export ZOTERO_API_KEY="your-key-from-zotero.org"
Rscript zotero_config_helper.R
```

### Step 2: Review the Output

The script will show:
- Your user ID (for personal library)
- All groups you're a member of
- All collections in each group
- Preview of items in each collection

### Step 3: Update Your Configuration

Edit `biospace_network_pipeline.R` and update these lines:

```r
ZOTERO_API_KEY <- "your-api-key"
LIBRARY_ID <- "2810748"          # From helper output
LIBRARY_TYPE <- "group"          # 'user' or 'group'
TARGET_COLLECTION <- "U4SW8TCS"  # From helper output (collection key)
```

---

## Key API Endpoints

| Purpose | Endpoint | Example |
|---------|----------|---------|
| User info | `/users/me` | Get your user ID |
| List groups | `/groups` | Get all groups you're in |
| List collections (user) | `/users/{id}/collections` | Get user collections |
| List collections (group) | `/groups/{id}/collections` | Get group collections |
| Get top-level items | `/users/{id}/collections/{key}/items/top` | Get items in collection |
| Get all items (nested) | `/users/{id}/collections/{key}/items` | Get all items including sub-collections |

---

## Common Configuration Scenarios

### Scenario 1: Personal Zotero Library

```r
LIBRARY_TYPE <- "user"
LIBRARY_ID <- "XXXXXXX"            # Your user ID (from helper)
TARGET_COLLECTION <- "ABCDEFGH"    # Your collection key
```

### Scenario 2: Group Library (Shared)

```r
LIBRARY_TYPE <- "group"
LIBRARY_ID <- "2810748"              # Group ID
TARGET_COLLECTION <- "U4SW8TCS"      # Collection key within group
```

### Scenario 3: Using Root of Library (No Collection)

For items at root level (not in a collection), use `/items/top` without `/collections/{key}`:

```r
# Would need to modify the URL construction in the script
base_url <- sprintf(
  "https://api.zotero.org/%s/%s/items/top",
  LIBRARY_TYPE,
  LIBRARY_ID
)
```

---

## Zotero API Authentication

### Getting Your API Key

1. Go to https://www.zotero.org/settings/keys
2. Click "Create new private key"
3. Copy the key
4. Set in environment:
   ```bash
   export ZOTERO_API_KEY="your-key-here"
   ```

### Verify Authentication

```bash
# Test if your API key works
curl "https://api.zotero.org/users/me?key=YOUR_API_KEY"
```

If successful, you'll get JSON with your user info.

---

## Testing Different Endpoints

### Test 1: Check if you can access your user info

```bash
curl "https://api.zotero.org/users/me?key=YOUR_API_KEY"
```

**Expected:** JSON object with your user ID and library ID

### Test 2: Check if you can access the group

```bash
curl "https://api.zotero.org/groups/2810748?key=YOUR_API_KEY"
```

**Expected:** JSON object with group info

### Test 3: Check if you can list collections in the group

```bash
curl "https://api.zotero.org/groups/2810748/collections?key=YOUR_API_KEY"
```

**Expected:** Array of collection objects with their keys

### Test 4: Check if you can get items from a collection

```bash
curl "https://api.zotero.org/groups/2810748/collections/U4SW8TCS/items/top?key=YOUR_API_KEY&limit=5"
```

**Expected:** Array of publication items (with `/top` endpoint)

---

## What `/items/top` vs `/items` means

| Endpoint | Behavior | Use When |
|----------|----------|----------|
| `/collections/{key}/items/top` | Returns items directly in the collection (not nested items in sub-collections) | You want items visible at that collection level |
| `/collections/{key}/items` | Returns all items including those in nested sub-collections | You want all nested items too |

For BioSCape, using `/items/top` is correct if publications are directly in the collection.

---

## Updated Script Improvements

The updated `biospace_network_pipeline.R` now:

1. ✓ Uses correct `/items/top` endpoint
2. ✓ Shows the API URL being called (for debugging)
3. ✓ Shows HTTP status code
4. ✓ Provides clearer error messages with configuration values
5. ✓ Checks if response contains items before processing
6. ✓ Suggests running `zotero_config_helper.R` on error

---

## Quick Fix Checklist

- [ ] API key is set: `echo $ZOTERO_API_KEY`
- [ ] API key is valid: `curl "https://api.zotero.org/users/me?key=$ZOTERO_API_KEY"`
- [ ] Group ID is correct (2810748 seems right)
- [ ] Collection ID is correct (check with helper script)
- [ ] Collection is not empty
- [ ] Using `/items/top` endpoint (not `/items`)
- [ ] Using query parameter `key=` (not Bearer authorization)

---

## Get Help

Run diagnostic script:

```bash
Rscript zotero_config_helper.R
```

This will tell you exactly what your correct configuration should be.

Then copy-paste the configuration it recommends into the main script.

---

**Last Updated:** February 16, 2026
