# Overview

This is a personal website for Kshitiz Jaiswal, an "Unfiltered Commentator" who creates social commentary content. The website serves as a platform to showcase reels with detailed analysis, conduct opinion polls, manage a newsletter subscription, and provide an admin interface for content management. The site emphasizes truth-telling and unbiased commentary with sections for video content analysis, interactive polls, and subscriber engagement.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Web Framework
- **Flask Application**: Built using Flask with a modular structure separating routes, models, forms, and utilities
- **Template Engine**: Uses Jinja2 templating with a base template system for consistent UI
- **Static Asset Management**: CSS, JavaScript, and uploaded files served through Flask's static file handling

## Data Storage
- **JSON-based Storage**: Simple file-based data management using JSON files instead of a traditional database
- **File Structure**: Separate JSON files for content, polls, and subscribers stored in a `/data` directory
- **Data Manager Class**: Centralized data access layer with methods for loading and saving JSON data

## Frontend Architecture
- **Responsive Design**: Bootstrap 5 framework for mobile-first responsive layouts
- **Custom Styling**: CSS custom properties for theming with modern gradient and shadow systems
- **Interactive Elements**: JavaScript for carousel animations, smooth scrolling, poll voting, and form handling
- **Progressive Enhancement**: Core functionality works without JavaScript, enhanced with interactive features

## Content Management
- **Admin Panel**: Secure admin interface for managing reels, opinions, subscribers, and content
- **Form Handling**: WTForms integration for server-side form validation and CSRF protection
- **File Upload System**: Image upload and processing with PIL for thumbnail generation and optimization
- **Content Types**: Support for reels (with video analysis), opinions (with polls), and newsletter content

## Authentication & Security
- **Session-based Admin Auth**: Simple session management for admin access with secure password hashing
- **CSRF Protection**: Flask-WTF CSRF tokens on all forms
- **File Upload Security**: Secure filename handling and file type validation
- **Environment Variables**: Sensitive configuration stored in environment variables

## Key Features
- **Auto-scrolling Carousel**: Infinite scroll reel display with smooth animations
- **Interactive Polling System**: Real-time voting on opinion pieces with percentage calculations  
- **Newsletter Subscription**: User registration with demographic data collection
- **Detailed Content Analysis**: "Behind the Reel" pages with sources, context, and analysis
- **Mobile-optimized Design**: Touch-friendly interface with responsive breakpoints

# External Dependencies

## Payment Integration
- **Razorpay**: Payment gateway integration for donations/support functionality
- **Environment Configuration**: API keys managed through environment variables

## Frontend Libraries
- **Bootstrap 5**: CSS framework for responsive components and utilities
- **Font Awesome**: Icon library for UI elements and visual hierarchy
- **Google Fonts**: Typography using Montserrat and Poppins font families

## Python Packages
- **Flask**: Core web framework
- **Flask-WTF**: Form handling and CSRF protection
- **WTForms**: Form validation and rendering
- **Werkzeug**: WSGI utilities and security helpers
- **Pillow (PIL)**: Image processing for upload optimization

## Image/Media Sources
- **Pixabay**: External image hosting for thumbnails and banner content
- **File Upload System**: Local storage for user-uploaded content with image processing

## Development & Deployment
- **ProxyFix Middleware**: Configured for deployment behind reverse proxies
- **Debug Mode**: Development configuration with detailed error reporting
- **Static File Serving**: Flask static file handling for CSS, JS, and uploads