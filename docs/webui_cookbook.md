# Managing CV JSON in Web UI

This guide covers how to use the CV JSON Manager web interface to browse, edit, and manage your CV data across multiple languages.

## Getting Started

### Starting the Web UI

```bash
cvgen web tags
```

Open http://127.0.0.1:5000 in your browser.

### Authentication (Optional)

Set up authentication for additional security:

```bash
# Combined format
export CVGEN_WEB_AUTH=username:password

# Or separate variables
export CVGEN_WEB_USER=username
export CVGEN_WEB_PASSWORD=password
```

## Navigation Overview

The Web UI has four main areas:

1. **Top Bar** - Navigation links and language selector
2. **Home Page** - Person selector (list of CV profiles)
3. **Person Dashboard** - Section navigation and export controls
4. **Entry Views** - List view, detail view, and edit forms

### Language Selector

The top bar includes a language selector (EN | DE | FA):

- Click a language code to switch display language
- Tags will show localized labels for the selected language
- Export preview reflects the selected language

## Common Tasks

### Browsing CV Entries

1. Click on a person from the home page
2. Select a section (Projects, Experiences, etc.)
3. Browse entries in list view
4. Click an entry to see details

### Editing an Entry

1. Navigate to the entry detail page
2. Click **Edit Entry**
3. Modify fields as needed
4. Optionally enable "Sync shared fields" to update URL/date across languages
5. Click **Save Changes**

### Creating a New Entry

1. Go to a section (e.g., Projects)
2. Click **Add New**
3. Fill in the required fields
4. Enable "Sync to all languages" to create the entry in EN/DE/FA
5. Click **Create Entry**

### Managing Tags

#### Creating a Tag

1. Go to **Tags** from the top navigation
2. Click **+ Create Tag**
3. Enter the tag name (use English as canonical ID)
4. Add an optional description
5. Click **Create**

#### Assigning Tags to Entries

1. Navigate to an entry detail page
2. Select/deselect tags from the checkbox list
3. Click **Update Tags**

#### Deleting a Tag

1. Go to **Tags** page
2. Click **Delete** next to the tag
3. Confirm the deletion (this removes the tag from all entries)

### Previewing Export

Before exporting to a file:

1. Go to a person's dashboard
2. Click **👁️ Preview Export**
3. Review the JSON that will be exported
4. Switch languages to see localized versions
5. Click **💾 Export to File** when ready

### Using Diagnostics

The Diagnostics page helps identify issues in your CV data:

1. Click **Diagnostics** in the top navigation
2. Review:
   - Database health status
   - Unused tags
   - Entries needing translation
   - Missing language counterparts

#### Cleaning Up Orphan Tags

If you see orphan tag references:

1. Go to **Diagnostics**
2. Click **Clean Up Orphan Tag References**
3. Confirm the action
4. Orphan tag references will be removed from entries

## Multi-Language Workflow

### Creating Entries in All Languages

When creating a new entry, enable "Sync to all languages" to:

1. Create the entry in the source language (EN by default)
2. Auto-create placeholder entries in DE and FA
3. Mark non-source entries as "needs translation"

### Checking Translation Status

1. Go to **Diagnostics**
2. Look for "Entries Needing Translation" section
3. Click on entries to navigate to them for translation

### Viewing Linked Entries

1. Navigate to an entry detail page
2. Click **View Linked Entries**
3. See all language variants of the same entry
4. Navigate between them to compare content

## Tips & Best Practices

### Tag Naming

- Use English names as canonical tag IDs (e.g., "Full CV", "Academic")
- Add translations in the tag catalog for localized display
- Keep tag names concise and descriptive

### Shared Fields

Some fields sync across languages automatically:

- **Projects**: URL, type_key
- **Publications**: DOI, identifiers, year, status
- **Education**: dates, GPA, logo URL
- **Experiences**: type_key

### Export Strategy

- Preview before exporting to catch issues
- Export to `output/json/` (not `data/`) to preserve source data
- Use language-specific exports for localized CVs

## Troubleshooting

### Tags Not Showing Translations

**Problem**: Tags display English labels even when language is set to DE/FA.

**Solution**: The tag catalog may not have translations. Currently, only built-in tags have translations. Custom tags use the canonical ID as fallback.

### Entry Not Found

**Problem**: Clicking an entry link shows "Entry not found".

**Solution**: The entry may have been deleted. Check the Diagnostics page for orphaned entries.

### Export Preview Shows Old Data

**Problem**: Preview doesn't reflect recent changes.

**Solution**: The preview regenerates from the database source of truth. If changes were made to JSON files directly, re-import them with `cvgen db import`.

### Orphan Tag References

**Problem**: Entries have tags that don't exist in the tag catalog.

**Solution**: Use the "Clean Up Orphan Tag References" action on the Diagnostics page.

### Missing Language Counterparts

**Problem**: Some entries exist only in EN, not DE/FA.

**Solution**: 
1. Check Diagnostics for "Missing Language Variants"
2. Create new entries with "Sync to all languages" enabled
3. Or manually create entries in each language with matching stable IDs

## Related Documentation

- [SQLite Tagging Cookbook](sqlite_tagging_cookbook.md) - Database operations
- [Language-Aware Tagging](language_aware_tagging.md) - Multi-language tag strategy
- [Multi-Language CRUD](multi_language_crud.md) - Entry synchronization
