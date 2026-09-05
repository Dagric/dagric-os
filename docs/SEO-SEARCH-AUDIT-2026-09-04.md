# Dagric OS website SEO and search audit

Date: 2026-09-04

Business: IMPRESSIONSDIRECT360 LLC

Product and fictitious name: Dagric OS

## Outcome

The website now has a public, crawlable topic directory; a Windows-switching
landing page written around the questions prospective users ask; a real-time
video library; more descriptive page titles; stronger internal linking; and
machine-readable product, organization, website, article, FAQ, and video data.

These changes improve eligibility for discovery. They do not guarantee a
particular ranking or rich result. Search engines choose what to crawl, index,
and display.

## Implemented

- Added `/search`, with server-rendered links to every public top-level page and
  an in-page filter for terms such as Wi-Fi, Windows files, task manager,
  recovery, privacy, and installation.
- Added `/switch-from-windows`, covering hardware testing, file and bookmark
  migration, application compatibility, backups, recovery, and installation.
- Added `/videos`, containing separate 15-, 30-, and 60-second continuous
  recordings. The page does not autoplay multiple videos or place a second
  video over the first.
- Added `WebSite`, `Organization`, and `SoftwareApplication` JSON-LD to the home
  page; `SoftwareApplication` JSON-LD to the Pro page; three `VideoObject`
  records to the video page; and `Article` data to the Windows-switching guide.
- Added video entries to the XML sitemap and refreshed modification dates for
  materially edited pages.
- Added an OpenSearch description so compatible browsers can recognize Dagric
  OS search.
- Added a public IndexNow key and a guarded submission utility. It defaults to a
  dry run and can notify participating search engines after the updated site is
  deployed.
- Added the Google Search Console URL-prefix property and its persistent HTML
  verification tag so sitemap submission and indexing reports can be managed
  from the signed-in owner account.
- Rewrote generic titles on the home, features, download, Pro, getting started,
  support, FAQ, news, privacy, security, licenses, review, testing, contact, and
  bug-report pages around their actual subject.
- Added search links to the main entry-point navigation and connected the home
  page to the Windows guide, videos, test proof, and topic directory.
- Kept the public company identity consistent: IMPRESSIONSDIRECT360 LLC is the
  legal organization and Dagric OS is the product/brand.
- Removed an externally hosted Launchory badge image that the site's own content
  security policy could block; the verified outbound listing link remains.
- Updated Firebase cache rules for the new pages and discovery files, including
  the OpenSearch MIME type.

## Validation

`python tools/audit-site.py` currently checks all 30 deployed HTML pages for:

- one unique title, description, H1, and canonical URL;
- working local links, images, video posters, and media sources;
- image alternatives and required video controls;
- valid JSON-LD;
- required website/software/video structured-data records;
- three complete video-sitemap records;
- crawl links from the public search directory;
- consistent social links and the correct business name; and
- retired composed-video references.

The three feature recordings also pass media probing as H.264, 1920×1080,
30 fps video with stereo AAC audio. Their measured lengths are exactly 15, 30,
and 60 seconds.

## Discovery submissions completed

- Deployed the audited site to Firebase Hosting and verified the new production
  pages, sitemap, OpenSearch document, and IndexNow key all return HTTP 200 from
  `https://dagric.com`.
- Added and verified the `https://dagric.com/` URL-prefix property in Google
  Search Console using the published HTML meta tag.
- Submitted `https://dagric.com/sitemap.xml`. Search Console reported that it
  processed successfully and discovered 28 public page URLs.
- Added the updated home page, `/switch-from-windows`, and `/videos` to Google's
  priority crawl queue. The home page was already indexed; the two new pages
  were not yet indexed at submission time.
- Google's live Rich Results Test found one valid Software App item on the home
  page and three valid Video items on `/videos`. The only home-page notice was
  the optional `aggregateRating`; no rating was added because the site does not
  have verified review data to support one.
- Submitted all 28 sitemap URLs to IndexNow. The service accepted the batch with
  HTTP 202.

## Next measurement cycle

1. Check Search Console after its initial reports finish processing, normally
   no sooner than the next day.
2. Validate the Pro, FAQ, and Windows-switching pages in Google's Rich Results
   Test when their corresponding Google result types or reports are relevant.
3. Measure impressions and queries for at least four weeks before rewriting
   pages again. Expand pages only where real search-query data shows unmet
   intent.

## Primary guidance used

- Google Search Central, SEO Starter Guide:
  https://developers.google.com/search/docs/fundamentals/seo-starter-guide
- Google Search Central, title links:
  https://developers.google.com/search/docs/appearance/title-link
- Google Search Central, crawlable links:
  https://developers.google.com/search/docs/crawling-indexing/links-crawlable
- Google Search Central, site names:
  https://developers.google.com/search/docs/appearance/site-names
- Google Search Central, SoftwareApplication structured data:
  https://developers.google.com/search/docs/appearance/structured-data/software-app
- Google Search Central, video SEO and video sitemaps:
  https://developers.google.com/search/docs/appearance/video
  https://developers.google.com/search/docs/crawling-indexing/sitemaps/video-sitemaps
- Bing Webmaster Tools, IndexNow:
  https://www.bing.com/indexnow/getstarted
