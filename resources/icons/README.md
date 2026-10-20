# Support CRM Icons

This directory contains Material Design style SVG icons for the Support CRM application.

## Available Icons

| Icon Name | Usage | Description |
|-----------|-------|-------------|
| `families.svg` | Navigation, Family views | Group of people icon |
| `payments.svg` | Navigation, Payment views | Credit card icon |
| `import.svg` | Navigation, Import buttons | Download/import arrow icon |
| `reports.svg` | Navigation, Report generation | Bar chart icon |
| `add.svg` | Add/New buttons | Plus sign icon |
| `edit.svg` | Edit buttons | Pencil icon |
| `delete.svg` | Delete/Remove buttons | Trash bin icon |
| `search.svg` | Search/Browse buttons | Magnifying glass icon |
| `refresh.svg` | Refresh buttons | Circular arrow icon |
| `export.svg` | Export buttons | Upload/export arrow icon |
| `settings.svg` | Settings/Preferences | Gear icon |
| `language.svg` | Language selector | Globe icon |
| `package.svg` | Support packages | Package/box icon |
| `close.svg` | Close/Cancel buttons | X/close icon |
| `subscriptions.svg` | Subscriptions view | Subscription icon |
| `audit_log.svg` | Audit log view | Log/history icon |
| `email.svg` | Email functions | Email/envelope icon |
| `group.svg` | Group management | Group icon |
| `lock.svg` | Security/Login | Lock icon |
| `user.svg` | Single user | User icon |
| `users.svg` | Multiple users | Users icon |

## Usage

### In Python Code

```python
from resources.icons import get_icon

# Create a button with an icon
button = QPushButton(get_icon('add'), "Add New")

# Create an action with an icon
action = QAction(get_icon('refresh'), "Refresh", self)

# Get icon with custom size
icon = get_icon('families', size=32)
```

### Icon Loader API

The `IconLoader` class provides a singleton pattern for efficient icon loading with caching:

```python
from resources.icons import icon_loader

# Get an icon
icon = icon_loader.get_icon('edit')

# Get a pixmap
pixmap = icon_loader.get_pixmap('delete', size=24)
```

## Icon Format

- **Format**: SVG (Scalable Vector Graphics)
- **Style**: Material Design
- **Color**: currentColor (inherits from parent element)
- **Viewbox**: 24x24
- **Default Size**: 24x24 pixels (scalable)

## Customization

Icons use `fill="currentColor"` which means they inherit the color from the CSS/QSS styling. To change icon colors:

```css
/* In QSS stylesheet */
QPushButton {
    color: #2196F3;  /* Icons will be blue */
}

QPushButton:hover {
    color: #1976D2;  /* Icons will be darker blue on hover */
}
```

## Adding New Icons

To add a new icon:

1. Create an SVG file with Material Design style
2. Ensure viewBox is set to "0 0 24 24"
3. Use `fill="currentColor"` for color inheritance
4. Save the file in this directory with a descriptive name
5. The icon will be automatically available via `get_icon('icon_name')`

Example SVG structure:
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
  <path d="M..."/>
</svg>
```

## Performance

- Icons are cached after first load for optimal performance
- SVG format ensures crisp rendering at any size
- Minimal file size (< 1KB per icon)

## License

Icons are based on Material Design icons, which are available under the Apache License 2.0.
