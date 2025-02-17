# Crons are run in UTC time!

MAILTO=amo-crons@mozilla.com
DJANGO_SETTINGS_MODULE='settings_local'

HOME=/tmp

# Every 5 minutes
*/5 * * * * %(django)s auto_approve
# Every 5 minutes, minutes 1 through 60 past the hour
1-60/5 * * * * %(django)s git_extraction

# Once per hour
1 * * * * %(django)s auto_reject
5 * * * * %(django)s notify_about_auto_approve_delay
10 * * * * %(z_cron)s update_blog_posts
15 * * * * %(django)s send_pending_rejection_last_warning_notifications
20 * * * * %(z_cron)s addon_last_updated
25 * * * * %(z_cron)s hide_disabled_files
45 * * * * %(z_cron)s update_addon_appsupport
50 * * * * %(z_cron)s cleanup_extracted_file
55 * * * * %(z_cron)s unhide_disabled_files

# Four times per day
35 23,17,11,5 * * * %(z_cron)s auto_import_blocklist
35 18,12,6,0 * * * %(z_cron)s upload_mlbf_to_remote_settings

# Once per day
1 6 * * * %(django)s clear_old_user_data
30 6 * * * %(z_cron)s update_addon_hotness
30 9 * * * %(z_cron)s update_user_ratings
30 14 * * * %(z_cron)s category_totals
0 22 * * * %(z_cron)s gc


# Update ADI metrics from S3 once per day
00 12 * * * %(django)s download_counts_from_file

# Once per day after metrics import is done
30 12 * * * %(z_cron)s update_addon_total_downloads
35 12 * * * %(z_cron)s update_addon_weekly_downloads
30 13 * * * %(z_cron)s update_addon_average_daily_users
00 14 * * * %(z_cron)s index_latest_stats

# Once per week
1 9 * * 1 %(django)s review_reports
# Disabled for now, see https://github.com/mozilla/addons-server/issues/11790
# 0 15 * * 6 %(django)s process_addons --task=constantly_recalculate_post_review_weight


# Do not put crons below this line

MAILTO=root
