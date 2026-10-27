# Sloth Shoebox Windows App - Technical Documentation

## Overview

This document describes the Windows application build using Rust + Tauri, which provides a native Windows experience for The Sloth Shoebox expense ledger application. The app maintains the core privacy principles and functionality while adding a standalone desktop experience.

## Architecture

### Technology Stack

- **Rust**: Core programming language with memory safety and performance
- **Tauri**: Framework for building cross-platform desktop applications
- **React**: Frontend framework for the user interface
- **Tailwind CSS**: Styling framework matching the cash-memo design system
- **SQLite**: Local database (same as web version)
- **Ollama**: Local model runtime (same as web version)

### Key Components

1. **Core Logic**: Rust modules handling ingest, parsing, ledger operations
2. **Tauri Bridge**: Rust-Tauri bindings for system integration
3. **React Frontend**: Desktop UI with cash-memo design system
4. **File System**: Local file watching and management
5. **Privacy Protection**: No network calls in parse path

## Design System

The Windows app maintains the same cash-memo aesthetic as the web version:

- **Colors**: Ink (structure), Pen (actions), Red (errors), Yellow (highlights), Moss (committed)
- **Fonts**: Archivo (body), Kalam (handwriting)
- **Layout**: Left-aligned, sentence-case headings, ruled tables
- **Motion**: Orchestrated animations with reduced motion support

## Onboarding & System Requirements

### RAM Detection & Model Selection

The app includes intelligent onboarding that detects system RAM and recommends appropriate models:

```rust
#[derive(Debug, Clone)]
pub enum RamLevel {
    Low,      // 8-11 GB
    Medium,   // 12-15 GB  
    High,     // 16-19 GB+
    VeryHigh, // 20+ GB
}
```

### Model Recommendations by RAM

| RAM Range | Recommended Model | Notes |
|-----------|-------------------|-------|
| 8-11 GB | Moondream/MiniCPM-V | Low-end fallback, functional |
| 12-15 GB | Gemma 4 12B | Best balance for laptops |
| 16-19 GB | Qwen3.8-Vision 27B | Primary choice, 4-bit quant |
| 20+ GB | Qwen3.8-Vision 27B | Full precision, best accuracy |

### Ollama Model Downloads

Based on detected RAM, the app automatically downloads appropriate models:

```bash
# Low-end (8-11 GB)
ollama pull moondream

# Medium (12-15 GB)  
ollama pull gemma4:12b

# High-end (16-19 GB+)
ollama pull qwen3.8-vision:27b-q4
```

## Features

### Core Functionality

- **File Ingestion**: Drag-and-drop, folder watching, gallery picker
- **Deduplication**: Perceptual hashing and reference-number matching
- **Local Parsing**: Ollama-hosted vision model parsing
- **Schema Validation**: Strict Pydantic validation
- **SQLite Ledger**: Single-file local database
- **Exports**: CSV, XLSX, monthly digest
- **Offline Queries**: Natural language interface
- **Roommate Splits**: Settlement calculation engine

### Windows-Specific Features

- **System Tray**: Minimizes to system tray
- **File Associations**: .jpg, .png, .pdf file type handling
- **Protocol Handler**: sloth-shoebox:// deep linking
- **Installer**: Windows installer with admin privileges support
- **Updates**: Built-in updater (Tauri updater plugin)

## Privacy & Security

### Privacy Guarantees

- **No Network in Parse Path**: All parsing happens locally
- **No Accounts**: Zero authentication or user data collection
- **No Cloud Sync**: Everything stays on local machine
- **File Access Only**: No SMS, contacts, or other permissions

### Security Measures

- **Content Security Policy**: Browser-like protection
- **Sandboxed Rust**: Memory safety from Rust
- **Tauri Security**: Isolated web views
- **Local-Only Data**: SQLite database with no backups

## Development Setup

### Prerequisites

```bash
# Install Rust (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Add Rust to PATH (restart terminal required)
# Or use rustup: rustup override set stable
```

### Build & Run

```bash
# Development mode (hot reload)
cd sloth-shoebox/app-windows
cargo run --dev

# Production build
cargo tauri build

# Package for Windows
cargo tauri build --bundle.msi
```

### Testing

```bash
# Unit tests
cargo test

# Integration tests  
./scripts/test_windows.sh

# UI tests (if using playwright)
 cargo test --features e2e
```

## Configuration

### Environment Variables

Same as web version, plus Windows-specific:

```bash
# Core settings
SLOTH_HOST=127.0.0.1
SLOTH_PORT=8337
SLOTH_DB=%APPDATA%\\sloth-shoebox\\data\\sloth_shoebox.db

# Model settings  
SLOTH_PARSER=ollama
SLOTH_TEXT_MODEL=phi4-mini
SLOTH_VLM_MODEL=gemma4:12b

# Windows-specific
SLOTH_WINDOWS_UPDATER_ENABLED=true
SLOTH_SYSTEM_TRAY_ENABLED=true
```

## Performance Optimization

### Memory Management

- **Efficient Model Loading**: Lazy loading based on RAM
- **Garbage Collection**: Rust's memory safety prevents leaks
- **Resource Pooling**: Reuse HTTP connections and file handles

### UI Optimization

- **Virtual Scrolling**: Handle large transaction lists efficiently
- **Lazy Loading**: Load images and data on demand
- **Debounced Operations**: Prevent UI freezes from long operations

## Updating & Distribution

### Version Bumping

```bash
# Update version in Cargo.toml
cargo build --release

# Update version in Tauri config
cargo tauri build --config tauri.dev.toml
```

### Distribution

```bash
# Windows Installer
cargo tauri build --bundle.msi --bundle.icon=assets/icon.ico

# Portable version  
cargo tauri build --bundle.nsis --bundle.portable

# AppX Package
cargo tauri build --bundle.appx
```

## Localization

### Language Support

- **English**: Primary language
- **Spanish**: Spanish-speaking users
- **French**: French-speaking users
- **German**: German-speaking users

### Right-to-Left Support

Supports both LTR and RTL languages with proper text direction handling.

## Accessibility

### WCAG 2.1 Compliance

- **Keyboard Navigation**: Full keyboard accessibility
- **Screen Reader Support**: ARIA labels and announcements
- **High Contrast**: Customizable themes
- **Focus Management**: Clear focus indicators
- **Reduced Motion**: Respects system preferences

## Troubleshooting

### Common Issues

#### "Model not found"
```bash
ollama list
cargo run --features download-model
```

#### "Permission denied"
```bash
# Run as Administrator
cargo tauri build --ci
```

#### "Database locked"
```rust
// App uses exclusive lock on database file
// Close app and restart if issues occur
```

#### "UI not responding"
```bash
cargo install chrome::frame:: Recorder
# Record UI interactions
```

## Migration

### From Web Version

1. **Data Migration**: Automatic import of existing `data/sloth_shoebox.db`
2. **Settings Migration**: Convert `.env` settings to Windows registry or config file
3. **Model Migration**: Download equivalent Ollama models on new system

### From Other Expense Trackers

| Source | Import Method | Notes |
|--------|---------------|-------|
| Splitwise | Manual CSV import | Limited by free tier caps |
| Expensify | Manual CSV export | Export limitations |
| Manual Excel | CSV import | No parsing capabilities |

## Future Enhancements

### Planned Features

1. **Offline PWA Client**: LAN-only sync between phone and desktop
2. **Bank CSV Reconciliation**: Match statements with parsed receipts
3. **Community Merchant Packs**: User-contributed layout fine-tunes
4. **Warranty Linking**: Attach parsed purchases to product entries
5. **Multi-currency**: Offline exchange rate snapshots

### Technical Roadmap

- **Rust Edition**: Upgrade to Rust 2024 edition
- **Tauri Version**: Upgrade to latest stable
- **Frontend Framework**: Consider Yew or Leptos for native Rust UI
- **Package Format**: Add AppX and MSIX support
- **Build Optimization**: Incremental compilation for faster builds

## Code Quality

### Linting & Formatting

```bash
# Format code
cargo fmt

# Lint with Clippy
cargo clippy -- -D warnings

# Check code quality
cargo make check
```

### Testing Strategy

- **Unit Tests**: 90%+ coverage on core logic
- **Integration Tests**: Full pipeline testing
- **UI Tests**: Component and interaction testing
- **Performance Tests**: Memory and CPU benchmarking

## Contributing

### Development Guidelines

- **Code Style**: Follow Rust idioms and cash-memo design
- **Testing**: Write tests before implementing new features
- **Documentation**: Update README and technical docs
- **Privacy**: Never introduce network calls in parse path

### Pull Request Process

1. **Create branch** from `master`
2. **Run tests**: `cargo test && cargo make check`
3. **Commit changes**: Follow conventional commits
4. **Create PR**: Reference issue number
5. **Review**: Pair programming for UI changes
6. **Merge**: After CI passes

## License

MIT License - See LICENSE file for details

## Contact

For issues and feature requests, use the GitHub issue tracker.

---

*Generated: 2026-10-27*
*Last Updated: Current date*