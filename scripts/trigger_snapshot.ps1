# Start the Daily snapshot workflow on GitHub. Run at 21:00 by Windows Task
# Scheduler on the desktop that serves as the Tailscale exit node; see
# docs/DATA-PIPELINE.md.
#
# GitHub delays scheduled runs by hours, so the desktop, which is on at that
# time anyway, asks for the run itself. The workflow's own cron is a backup.
#
# Needs a fine-grained personal access token for this repository only, with
# "Actions: Read and write", in the user environment variable
# STRAY_ATLAS_DISPATCH_TOKEN.

$ErrorActionPreference = 'Stop'

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

# A few tries: a desktop that has only just woken may not have its network up.
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
