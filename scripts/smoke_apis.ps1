[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    "PSAvoidUsingPlainTextForPassword",
    "",
    Justification = "Smoke test script accepts CLI input for local/dev automation."
)]
Param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$Email = "smoke.user@nirovaai.com",
    [string]$Password = "Pass1234!"
)

$ErrorActionPreference = "Stop"

$results = New-Object System.Collections.Generic.List[object]

function Add-Result {
    Param(
        [string]$Name,
        [string]$Status,
        [string]$Detail
    )
    $results.Add([PSCustomObject]@{
        endpoint = $Name
        status = $Status
        detail = $Detail
    }) | Out-Null
}

function Invoke-Json {
    Param(
        [string]$Method,
        [string]$Url,
        [object]$Body = $null,
        [Microsoft.PowerShell.Commands.WebRequestSession]$WebSession = $null,
        [int]$TimeoutSec = 20
    )

    $requestArgs = @{
        Uri = $Url
        Method = $Method
        TimeoutSec = $TimeoutSec
    }

    if ($null -ne $Body) {
        $requestArgs["ContentType"] = "application/json"
        $requestArgs["Body"] = ($Body | ConvertTo-Json -Depth 8 -Compress)
    }
    if ($null -ne $WebSession) {
        $requestArgs["WebSession"] = $WebSession
    }

    return Invoke-RestMethod @requestArgs
}

function Invoke-SmokeTest {
    $webSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $isAuthed = $false
    $mongoConnected = $false

    # 1) Health
    try {
        $health = Invoke-Json -Method "GET" -Url "$BaseUrl/health"
        $mongoConnected = [bool]$health.mongo_connected
        Add-Result -Name "GET /health" -Status "PASS" -Detail ("mode={0}, mongo_connected={1}" -f $health.mode, $health.mongo_connected)
    }
    catch {
        Add-Result -Name "GET /health" -Status "FAIL" -Detail $_.Exception.Message
    }

    # 2) CORS preflight for login
    try {
        $cors = Invoke-WebRequest -UseBasicParsing -Method Options -Uri "$BaseUrl/auth/login" -Headers @{
            Origin = "http://localhost:5174"
            "Access-Control-Request-Method" = "POST"
            "Access-Control-Request-Headers" = "content-type,authorization"
        } -TimeoutSec 15
        Add-Result -Name "OPTIONS /auth/login" -Status "PASS" -Detail ("status={0}" -f $cors.StatusCode)
    }
    catch {
        Add-Result -Name "OPTIONS /auth/login" -Status "FAIL" -Detail $_.Exception.Message
    }

    if (-not $mongoConnected) {
        Add-Result -Name "POST /auth/register" -Status "SKIP" -Detail "MongoDB disconnected (degraded mode)"
        Add-Result -Name "POST /auth/login" -Status "SKIP" -Detail "MongoDB disconnected (degraded mode)"
        Add-Result -Name "GET /auth/me" -Status "SKIP" -Detail "MongoDB disconnected (degraded mode)"
        Add-Result -Name "POST /symptoms/predict" -Status "SKIP" -Detail "MongoDB disconnected (degraded mode)"
        Add-Result -Name "GET /symptoms/history" -Status "SKIP" -Detail "MongoDB disconnected (degraded mode)"
        Add-Result -Name "GET /symptoms/latest" -Status "SKIP" -Detail "MongoDB disconnected (degraded mode)"
        Add-Result -Name "GET /health/timeline" -Status "SKIP" -Detail "MongoDB disconnected (degraded mode)"
        Add-Result -Name "GET /health/alerts" -Status "SKIP" -Detail "MongoDB disconnected (degraded mode)"
        Add-Result -Name "GET /health/summary" -Status "SKIP" -Detail "MongoDB disconnected (degraded mode)"
        Add-Result -Name "POST /chat/ask" -Status "SKIP" -Detail "MongoDB disconnected (degraded mode)"
    }
    else {
    # 3) Register (or login if already exists)
    try {
        $registerBody = @{
            name = "Smoke User"
            email = $Email
            password = $Password
            age = 27
            district = "Dhaka"
            language = "en"
        }
        Invoke-Json -Method "POST" -Url "$BaseUrl/auth/register" -Body $registerBody -WebSession $webSession -TimeoutSec 20 | Out-Null
        Add-Result -Name "POST /auth/register" -Status "PASS" -Detail "registered"
    }
    catch {
        $msg = $_.Exception.Message
        if ($msg -match "400|already exists") {
            Add-Result -Name "POST /auth/register" -Status "PASS" -Detail "already exists (expected)"
        }
        else {
            Add-Result -Name "POST /auth/register" -Status "FAIL" -Detail $msg
        }
    }

    # 4) Login
    try {
        $loginBody = @{
            email = $Email
            password = $Password
        }
        $login = Invoke-Json -Method "POST" -Url "$BaseUrl/auth/login" -Body $loginBody -WebSession $webSession -TimeoutSec 20
        Add-Result -Name "POST /auth/login" -Status "PASS" -Detail ("user={0}" -f $login.email)
    }
    catch {
        Add-Result -Name "POST /auth/login" -Status "FAIL" -Detail $_.Exception.Message
    }

    # 5) Me profile
    try {
        $me = Invoke-Json -Method "GET" -Url "$BaseUrl/auth/me" -WebSession $webSession
        $isAuthed = $true
        Add-Result -Name "GET /auth/me" -Status "PASS" -Detail ("name={0}" -f $me.name)
    }
    catch {
        Add-Result -Name "GET /auth/me" -Status "FAIL" -Detail $_.Exception.Message
    }

    # 6) Symptoms predict
    if ($isAuthed) {
        try {
            $predictBody = @{
                symptoms = @("fever", "headache")
                age = 27
                district = "Dhaka"
                language = "en"
            }
            $predict = Invoke-Json -Method "POST" -Url "$BaseUrl/symptoms/predict" -WebSession $webSession -Body $predictBody -TimeoutSec 30
            $primary = $predict.prediction.disease_prediction.predicted_disease
            Add-Result -Name "POST /symptoms/predict" -Status "PASS" -Detail ("predicted={0}" -f $primary)
        }
        catch {
            Add-Result -Name "POST /symptoms/predict" -Status "FAIL" -Detail $_.Exception.Message
        }
    }

    # 7) Symptoms history
    if ($isAuthed) {
        try {
            $history = Invoke-Json -Method "GET" -Url "$BaseUrl/symptoms/history?limit=5" -WebSession $webSession
            $count = 0
            if ($history.history) { $count = $history.history.Count }
            Add-Result -Name "GET /symptoms/history" -Status "PASS" -Detail ("entries={0}" -f $count)
        }
        catch {
            Add-Result -Name "GET /symptoms/history" -Status "FAIL" -Detail $_.Exception.Message
        }
    }

    # 8) Latest symptoms
    if ($isAuthed) {
        try {
            Invoke-Json -Method "GET" -Url "$BaseUrl/symptoms/latest" -WebSession $webSession | Out-Null
            Add-Result -Name "GET /symptoms/latest" -Status "PASS" -Detail "ok"
        }
        catch {
            Add-Result -Name "GET /symptoms/latest" -Status "FAIL" -Detail $_.Exception.Message
        }
    }

    # 9) Health timeline
    if ($isAuthed) {
        try {
            $timeline = Invoke-Json -Method "GET" -Url "$BaseUrl/health/timeline?days=7" -WebSession $webSession
            $count = 0
            if ($timeline.timeline) { $count = $timeline.timeline.Count }
            Add-Result -Name "GET /health/timeline" -Status "PASS" -Detail ("points={0}" -f $count)
        }
        catch {
            Add-Result -Name "GET /health/timeline" -Status "FAIL" -Detail $_.Exception.Message
        }
    }

    # 10) Health alerts
    if ($isAuthed) {
        try {
            $alerts = Invoke-Json -Method "GET" -Url "$BaseUrl/health/alerts" -WebSession $webSession
            $count = 0
            if ($alerts.alerts) { $count = $alerts.alerts.Count }
            Add-Result -Name "GET /health/alerts" -Status "PASS" -Detail ("alerts={0}" -f $count)
        }
        catch {
            Add-Result -Name "GET /health/alerts" -Status "FAIL" -Detail $_.Exception.Message
        }
    }

    # 11) Health summary
    if ($isAuthed) {
        try {
            Invoke-Json -Method "GET" -Url "$BaseUrl/health/summary" -WebSession $webSession -TimeoutSec 40 | Out-Null
            Add-Result -Name "GET /health/summary" -Status "PASS" -Detail "ok"
        }
        catch {
            Add-Result -Name "GET /health/summary" -Status "FAIL" -Detail $_.Exception.Message
        }
    }

    # 12) Chat ask
    if ($isAuthed) {
        try {
            $chatBody = @{
                message = "I have fever and body pain. What should I do?"
                language = "en"
            }
            $chat = Invoke-Json -Method "POST" -Url "$BaseUrl/chat/ask" -WebSession $webSession -Body $chatBody -TimeoutSec 45
            $len = 0
            if ($chat.response) { $len = $chat.response.Length }
            Add-Result -Name "POST /chat/ask" -Status "PASS" -Detail ("response_chars={0}" -f $len)
        }
        catch {
            Add-Result -Name "POST /chat/ask" -Status "FAIL" -Detail $_.Exception.Message
        }
    }
    }
}

Invoke-SmokeTest

Write-Host ""
Write-Host "NirovaAI API Smoke Test Results"
Write-Host "--------------------------------"
$results | Format-Table -AutoSize

$failCount = ($results | Where-Object { $_.status -eq "FAIL" } | Measure-Object).Count
Write-Host ""
if ($failCount -eq 0) {
    Write-Host "ALL CHECKS PASSED" -ForegroundColor Green
    exit 0
}
else {
    Write-Host ("FAILED CHECKS: {0}" -f $failCount) -ForegroundColor Red
    exit 1
}
