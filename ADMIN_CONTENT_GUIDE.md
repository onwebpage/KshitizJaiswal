# Admin Panel - Content Management Guide

## Overview
Your admin panel now provides comprehensive control over virtually all website content. The navigation has been reorganized into clear sections for easy access.

## Accessing the Admin Panel
- URL: `/admin/login`
- Default credentials are set via environment variables: `ADMIN_USERNAME` and `ADMIN_PASSWORD`

---

## 📝 CONTENT MANAGEMENT

### 1. **Page Content** (`/admin/page-content`)
Edit text content that appears throughout your website:
- **Reels Section**
  - Section title (e.g., "Beyond The Reel")
  - Section subtitle
- **Support Section**
  - Section title (e.g., "Friends of Kshitiz — Support Now")
  - Section subtitle
  - Custom support button text
  - Custom support subtitle
- **Support Statistics**
  - Supporter count display
  - Amount raised this month

### 2. **Hero Section** (`/admin/hero-content`)
Edit the main banner/hero area of your homepage:
- Hero title/name
- Hero tagline
- Desktop hero image (upload or URL)
- Mobile hero image (upload or URL)
- Legacy banner image support

### 3. **Learning Resources** (`/admin/resources`)
Manage educational content offerings:
- Add/edit/delete learning resources
- Set titles, descriptions, pricing
- Upload resource images
- Set external links

### 4. **Upcoming Shows** (`/admin/shows`)
Manage your show schedule:
- Add/edit/delete shows
- Set show titles and descriptions
- Upload show images
- Mark as "Coming Soon" or "Available Now"
- Add notification/registration links

### 5. **Site Settings** (`/admin/site-settings`)
Configure global site settings:
- Site title and tagline
- Contact email
- Social media links (Facebook, Twitter, Instagram, YouTube)
- SEO meta description and keywords
- Google Analytics ID
- Facebook Pixel ID

### 6. **Social Links** (`/admin/social-links`)
Manage social media presence:
- Add/edit/delete social platforms
- Set platform URLs
- Choose icons
- Toggle visibility
- Reorder links

---

## 🎬 MEDIA & POSTS

### 7. **Manage Reels** (Dashboard → Reels tab or `/admin/reel/add`)
Full control over video content:
- Add new reels
- Edit existing reels (title, thumbnail, video URL)
- Behind-the-thought explanations
- Source citations
- Extra context
- Category tags (trending, new, must_watch, etc.)
- Topic tags for playlists
- Feature reels on homepage
- Bulk operations available

### 8. **Manage Opinions/Polls** (Dashboard → Opinions tab or `/admin/opinion/add`)
Create and manage interactive polls:
- Add new opinions/polls
- Edit poll questions and options
- Set your position on topics
- Add descriptions
- Topic tagging
- View poll results in real-time
- Track total votes

### 9. **Media Library** (`/admin/media-library`)
Centralized media management:
- Upload and organize images
- View all uploaded media
- Use in other content areas

---

## 💰 REVENUE & COURSES

### 10. **Subscription Tiers** (`/admin/subscription-tiers`)
Manage supporter pricing plans:
- Create/edit/delete subscription tiers
- Set prices and billing periods (week/month/year)
- Add tier descriptions
- List benefits for each tier
- Choose Font Awesome icons
- Mark popular tiers
- Set display order
- Toggle active/inactive status

### 11. **Payment Settings** (`/admin/payment-settings`)
Configure payment processing:
- Razorpay API Key ID
- Razorpay API Key Secret
- Test/Live mode configuration

### 12. **Courses** (`/admin/courses`)
Educational course management:
- Create/edit courses
- Set course titles, descriptions, thumbnails
- Set pricing
- Manage course structure (modules and lessons)

### 13. **Modules** (`/admin/modules`)
Organize course content:
- Create modules within courses
- Set module titles and descriptions
- Order modules

### 14. **Lessons** (`/admin/lessons`)
Individual lesson content:
- Create lessons within modules
- Upload video URLs (YouTube unlisted/private)
- Add lesson notes and resources
- Set lesson duration
- Order lessons

---

## 👥 USERS & ANALYTICS

### 15. **Subscribers** (Dashboard → Subscribers tab)
View newsletter subscribers:
- See all subscriber information
- Export subscriber data to CSV
- View subscription dates

### 16. **User Management** (`/admin/users`)
Manage course enrollments:
- View users with course access
- Grant/revoke course access
- Track payment records

### 17. **Analytics** (`/admin/analytics`)
Track website performance:
- Total reels, opinions, subscribers, courses
- Most viewed reels
- Recent subscriber growth
- Poll engagement statistics
- Topic and category distribution

---

## 🔧 ADVANCED TOOLS

### 18. **Bulk Operations** (`/admin/bulk-operations`)
Efficient content management:
- Bulk delete reels
- Bulk feature/unfeature reels
- Mass content updates

### 19. **Column Visibility** (`/admin/column-visibility`)
Customize admin table views:
- Show/hide table columns
- Personalize your admin interface

### 20. **Email Broadcast** (`/admin/email-broadcast`)
Communication tools:
- Send emails to subscribers
- Broadcast announcements

### 21. **Activity Logs** (`/admin/activity-logs`)
Monitor admin actions:
- Track changes made in admin panel
- Audit trail for content updates

### 22. **Database Export** (`/admin/database-export`)
Backup and data portability:
- Export reels data as JSON
- Export opinions data
- Export subscriber lists
- Export course data
- Full database export

---

## 🎯 Quick Start Guide

### Most Common Content Edits

1. **Change Homepage Hero Banner**
   - Go to: Quick Actions → "Edit Hero Section"
   - Upload new images or paste image URLs
   - Update title and tagline

2. **Edit Page Text/Titles**
   - Go to: Quick Actions → "Edit Page Content"
   - Update section titles, subtitles, button text

3. **Add New Video/Reel**
   - Go to: Quick Actions → "Add New Reel"
   - Fill in title, upload thumbnail, add video URL
   - Add context and sources

4. **Manage Subscription Pricing**
   - Go to: Sidebar → "Subscription Tiers"
   - Edit prices, benefits, descriptions

5. **Update Social Media Links**
   - Go to: Sidebar → "Social Links"
   - Add/edit platform URLs

---

## 💡 Tips

- **All changes save to the database** - No need to manually backup files
- **Preview changes** - Use the view/preview links before publishing
- **Responsive images** - Upload both desktop and mobile versions for best results
- **SEO optimization** - Fill in meta descriptions in Site Settings
- **Regular backups** - Use Database Export to backup your content

---

## 📞 Need Help?

If you need to edit something that's not listed here, let me know and I can add more editing capabilities to the admin panel!
