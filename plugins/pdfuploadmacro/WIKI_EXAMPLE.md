# Example Wiki Page for PDF Upload and Textbook Display

This is an example of how to use the PDF upload and textbook display macros in a Trac wiki page.

## Wiki Markup

```wiki
= Educational Content Management =

Welcome to the LearnTrac educational content management system. This page allows you to upload new educational materials and browse existing textbooks.

== Upload New Textbook ==

Use the form below to upload a new PDF textbook to the system:

[[PDFUpload]]

== Available Textbooks ==

Browse our collection of uploaded textbooks:

[[TextbookList]]

== Filter by Subject ==

=== Computer Science Textbooks ===

[[TextbookList(subject=Computer Science,limit=10)]]

=== Mathematics Textbooks ===

[[TextbookList(subject=Mathematics,limit=10)]]

== Secure Upload Area ==

For authenticated uploads only:

[[PDFUpload(require_auth=true)]]
```

## Usage Notes

1. **TextbookList Macro**: Displays textbook cards from Neo4j
   - Basic usage: `[[TextbookList]]`
   - With filters: `[[TextbookList(subject=Mathematics,limit=10)]]`
   - Parameters:
     - `subject`: Filter by subject (e.g., Computer Science, Mathematics, Physics)
     - `limit`: Maximum number of textbooks to display (default: 20)

2. **PDFUpload Macro**: Provides upload form
   - Basic usage: `[[PDFUpload]]`
   - With authentication: `[[PDFUpload(require_auth=true)]]`
   - With pre-selected subject: `[[PDFUpload(subject=Computer Science)]]`

## Features

The textbook cards display:
- Subject category (color-coded badge)
- Title and authors
- Metadata (pages processed, chunks created, upload date)
- Action buttons:
  - 🔍 Search: Search within the textbook
  - 🌐 Explore: View concept graph
  - 📚 Paths: Generate learning paths

## Styling

The components are responsive and work on both desktop and mobile devices. The cards use a grid layout that automatically adjusts based on screen size.

## API Integration

Both macros integrate with the LearnTrac API:
- Upload endpoint: `POST /api/trac/textbooks/upload`
- List endpoint: `GET /api/trac/textbooks`

The API endpoint is configured in `trac.ini` under the `[learntrac]` section.