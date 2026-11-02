# Start the Daily snapshot workflow on GitHub. Run at 09:00 by Windows Task
# Scheduler on the laptop that serves as the Tailscale exit node; see
# docs/DATA-PIPELINE.md.
#
# GitHub delays scheduled runs by hours, so the laptop, which is on at that
# time anyway, asks for the run itself. The workflow's own crons are backups.
#
# Needs a fine-grained personal access token for this repository only, with
# "Actions: Read and write", in the user environment variable
# STRAY_ATLAS_DISPATCH_TOKEN, so the scheduled task must run as that user.

$ErrorActionPreference = 'Stop'

# Snapshots are taken between 09:00 and 12:59 Taipei time, so each one shows
# the feed at about the same time of day. Task Scheduler catches up on a start
# missed while the laptop was off; past 12:59 the day is left to the backup
# crons, the watchdog and a manual run.
# Fixed +08:00 rather than the laptop's time zone: Taiwan has no DST.
$taipei = [DateTime]::UtcNow.AddHours(8)
if ($taipei.Hour -lt 9 -or $taipei.Hour -ge 13) {
    Write-Output "it is $($taipei.ToString('HH:mm')) in Taipei, outside 09:00-12:59; not dispatching"
    exit 0
}

$token = [Environment]::GetEnvironmentVariable('STRAY_ATLAS_DISPATCH_TOKEN', 'User')
if (-not $token) {
    Write-Error 'STRAY_ATLAS_DISPATCH_TOKEN is not set'
    exit 1
}

$uri = 'https://api.github.com/repos/Jen-Chieh-Yu/stray-atlas/actions/workflows/daily-snapshot.yml/dispatches'
$headers = @{
    Authorization          = "Bearer $token"
    Accept                 = 'application/vnd.github+json'
    'X-GitHub-Api-Version' = '2022-11-28'
}
$body = @{ ref = 'main' } | ConvertTo-Json

# A few tries: a laptop that has only just woken may not have its network up.
for ($attempt = 1; $attempt -le 3; $attempt++) {
    try {
        Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -Body $body -ContentType 'application/json' | Out-Null
        Write-Output "dispatched Daily snapshot on attempt $attempt"
        exit 0
    } catch {
        Write-Warning "attempt $attempt failed: $($_.Exception.Message)"
        if ($attempt -lt 3) { Start-Sleep -Seconds 30 }
    }
}
exit 1
