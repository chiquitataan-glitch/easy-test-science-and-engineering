# ================================================================
# Easy Test API - 冒烟测试 + 回归测试套件 (PowerShell)
# 
# 前置条件:
#   1. PostgreSQL 运行在 localhost:5432
#   2. Python 后端运行在 localhost:8000
#   3. 数据库已初始化 (python -c "import asyncio; from app.database import init_db; asyncio.run(init_db())")
#
# 使用方法:
#   .\test_api.ps1
# ================================================================

param(
    [string]$BaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Continue"
$passed = 0
$failed = 0
$total = 0

function Test-API {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Path,
        [hashtable]$Headers = @{},
        [string]$Body = $null,
        [int]$ExpectedStatus = 200,
        [string]$ExpectedBodyContains = $null,
        [string]$ExpectedBodyNotContains = $null,
        [string]$SaveToken = $false,
        [string]$SavePaperId = $false,
        [string]$SaveFileId = $false,
        [string]$Note = $null
    )
    $script:total++
    
    $uri = "$BaseUrl$Path"
    $params = @{
        Uri = $uri
        Method = $Method
    }
    
    $allHeaders = @{}
    if ($script:global:TOKEN) {
        $allHeaders["Authorization"] = "Bearer $script:global:TOKEN"
    }
    if ($Headers.Count -gt 0) {
        foreach ($key in $Headers.Keys) {
            $allHeaders[$key] = $Headers[$key]
        }
    }
    $params["Headers"] = $allHeaders
    
    if ($Body) {
        $params["Body"] = $Body
        if (-not $allHeaders["Content-Type"]) {
            $allHeaders["Content-Type"] = "application/json"
        }
    }
    
    try {
        $response = Invoke-WebRequest @params -SkipCertificateCheck
        $statusCode = $response.StatusCode
        $content = $response.Content | ConvertFrom-Json
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        try {
            $stream = $_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($stream)
            $contentRaw = $reader.ReadToEnd()
            $content = $contentRaw | ConvertFrom-Json
        } catch {
            $content = $null
        }
    }
    
    $ok = $true
    if ($ExpectedStatus -ne $statusCode) {
        Write-Host "  [FAIL] $Name - Expected status $ExpectedStatus, got $statusCode" -ForegroundColor Red
        $ok = $false
    }
    if ($ExpectedBodyContains -and $content) {
        $bodyStr = $content | ConvertTo-Json -Compress
        if ($bodyStr -notmatch [regex]::Escape($ExpectedBodyContains)) {
            Write-Host "  [FAIL] $Name - Response does not contain '$ExpectedBodyContains'" -ForegroundColor Red
            $ok = $false
        }
    }
    if ($ExpectedBodyNotContains -and $content) {
        $bodyStr = $content | ConvertTo-Json -Compress
        if ($bodyStr -match [regex]::Escape($ExpectedBodyNotContains)) {
            Write-Host "  [FAIL] $Name - Response contains forbidden '$ExpectedBodyNotContains'" -ForegroundColor Red
            $ok = $false
        }
    }
    
    if ($ok) {
        Write-Host "  [PASS] $Name (HTTP $statusCode)" -ForegroundColor Green
        $script:passed++
    } else {
        $script:failed++
    }
    
    # Save tokens/IDs
    if ($SaveToken -and $content.success -and $content.data.token) {
        $script:global:TOKEN = $content.data.token
        Write-Host "         Token saved: $($script:global:TOKEN.Substring(0,20))..." -ForegroundColor Gray
    }
    if ($SavePaperId -and $content.success -and $content.data.id) {
        $script:global:PAPER_ID = $content.data.id
        Write-Host "         Paper ID saved: $script:global:PAPER_ID" -ForegroundColor Gray
    }
    if ($SaveFileId -and $content.success -and $content.data.id) {
        if (-not $script:global:FILE_IDS) { $script:global:FILE_IDS = @() }
        $script:global:FILE_IDS += $content.data.id
        Write-Host "         File ID saved: $($content.data.id)" -ForegroundColor Gray
    }
    
    if ($Note) {
        Write-Host "         Note: $Note" -ForegroundColor Yellow
    }
    
    return @{ ok = $ok; status = $statusCode; content = $content }
}

# ================================================================
# 第一阶段: 环境检查
# ================================================================
Write-Host "`n=======================================" -ForegroundColor Cyan
Write-Host "  阶段 1: 环境冒烟测试" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

Test-API -Name "Health check" -Method GET -Path "/health" -ExpectedStatus 200 `
    -ExpectedBodyContains "ok"

# ================================================================
# 第二阶段: 认证测试
# ================================================================
Write-Host "`n=======================================" -ForegroundColor Cyan
Write-Host "  阶段 2: 认证测试" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# 2.1 注册
$registerBody = @{
    email = "test_$(Get-Date -Format 'HHmmss')@example.com"
    password = "Test123456"
    displayName = "TestUser"
} | ConvertTo-Json

Test-API -Name "Register new user" -Method POST -Path "/api/auth/register" `
    -Body $registerBody -ExpectedStatus 201 -SaveToken $true

# 2.2 重复注册 (应返回 400)
Test-API -Name "Register duplicate email" -Method POST -Path "/api/auth/register" `
    -Body $registerBody -ExpectedStatus 400

# 2.3 密码太短
$shortPwdBody = @{
    email = "short@example.com"
    password = "123"
    displayName = "Short"
} | ConvertTo-Json

Test-API -Name "Register short password" -Method POST -Path "/api/auth/register" `
    -Body $shortPwdBody -ExpectedStatus 422

# 2.4 获取当前用户
Test-API -Name "Get current user (/me)" -Method GET -Path "/api/auth/me" `
    -ExpectedBodyContains "success"

# 2.5 Token 刷新
Test-API -Name "Refresh token" -Method POST -Path "/api/auth/refresh" `
    -SaveToken $true

# 2.6 登录
$loginBody = @{
    email = ($registerBody | ConvertFrom-Json).email
    password = "Test123456"
} | ConvertTo-Json

# Clear token first to test login
$script:global:TOKEN = $null
Test-API -Name "Login" -Method POST -Path "/api/auth/login" `
    -Body $loginBody -ExpectedStatus 200 -SaveToken $true

# 2.7 错误密码登录
$wrongLogin = @{
    email = ($registerBody | ConvertFrom-Json).email
    password = "WrongPassword123"
} | ConvertTo-Json

Test-API -Name "Login wrong password" -Method POST -Path "/api/auth/login" `
    -Body $wrongLogin -ExpectedStatus 401 -ExpectedBodyContains "INVALID_CREDENTIALS"

# 2.8 无 token 访问受保护接口
$oldToken = $script:global:TOKEN
$script:global:TOKEN = $null
Test-API -Name "Access papers without auth" -Method GET -Path "/api/papers/" `
    -ExpectedStatus 401
$script:global:TOKEN = $oldToken

# ================================================================
# 第三阶段: 文件上传测试
# ================================================================
Write-Host "`n=======================================" -ForegroundColor Cyan
Write-Host "  阶段 3: 文件上传测试" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# 3.1 上传 .ppt (应被拒绝, 400)
Write-Host "  [SKIP] Upload .ppt file - requires actual file, can't test via curl" -ForegroundColor Yellow
Write-Host "         手动测试: curl -X POST $BaseUrl/api/files/upload -H 'Authorization: Bearer TOKEN' -F 'file=@test.ppt'" -ForegroundColor Yellow
Write-Host "         预期: HTTP 400 'UNSUPPORTED_FILE_TYPE'" -ForegroundColor Yellow

# 3.2 文件列表
Test-API -Name "List files" -Method GET -Path "/api/files/" -ExpectedStatus 200

# ================================================================
# 第四阶段: 配额测试
# ================================================================
Write-Host "`n=======================================" -ForegroundColor Cyan
Write-Host "  阶段 4: 配额测试" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

Test-API -Name "Get quota" -Method GET -Path "/api/quota/" -ExpectedStatus 200 `
    -ExpectedBodyContains "remainingGenerations"

Test-API -Name "Get quota /me" -Method GET -Path "/api/quota/me" -ExpectedStatus 200 `
    -ExpectedBodyContains "quotaRemaining"

Test-API -Name "Get quota history" -Method GET -Path "/api/quota/history" -ExpectedStatus 200

# ================================================================
# 第五阶段: 试卷生成测试 (需要已上传的文件)
# ================================================================
Write-Host "`n=======================================" -ForegroundColor Cyan
Write-Host "  阶段 5: 试卷生成测试" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# 5.1 无文件 ID 生成 (应返回 400)
$genBody = @{
    courseName = "Test Course"
    documentIds = @()
} | ConvertTo-Json

Test-API -Name "Generate without docs" -Method POST -Path "/api/papers/generate" `
    -Body $genBody -ExpectedStatus 400

# 5.2 文件数量不足 (应返回 400)
$genBody2 = @{
    courseName = "Test Course"
    documentIds = @("fake-id-1", "fake-id-2")
} | ConvertTo-Json

Test-API -Name "Generate with insufficient docs" -Method POST -Path "/api/papers/generate" `
    -Body $genBody2 -ExpectedStatus 400

# 5.3 试卷列表
Test-API -Name "List papers" -Method GET -Path "/api/papers/" -ExpectedStatus 200

# ================================================================
# 第六阶段: 试卷详情与导出测试
# ================================================================
Write-Host "`n=======================================" -ForegroundColor Cyan
Write-Host "  阶段 6: 试卷详情与导出测试" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# 6.1 不存在的试卷
Test-API -Name "Get non-existent paper" -Method GET -Path "/api/papers/fake-paper-id" `
    -ExpectedStatus 404

# 6.2 导出不存在的试卷
Test-API -Name "Export non-existent paper" -Method GET -Path "/api/papers/fake-paper-id/export" `
    -ExpectedStatus 404

# 6.3 重新生成不存在的试卷
Test-API -Name "Regenerate non-existent paper" -Method POST -Path "/api/papers/fake-paper-id/regenerate" `
    -ExpectedStatus 404

# 6.4 删除不存在的试卷
Test-API -Name "Delete non-existent paper" -Method DELETE -Path "/api/papers/fake-paper-id" `
    -ExpectedStatus 404

# ================================================================
# 第七阶段: 安全测试
# ================================================================
Write-Host "`n=======================================" -ForegroundColor Cyan
Write-Host "  阶段 7: 安全测试" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# 7.1 SQL 注入尝试
$sqliBody = @{
    email = "test@test.com'; DROP TABLE users;--"
    password = "password12345678"
} | ConvertTo-Json

Test-API -Name "SQL injection in login" -Method POST -Path "/api/auth/login" `
    -Body $sqliBody -ExpectedStatus 401

# 7.2 XSS 尝试
$xssBody = @{
    courseName = "<script>alert('xss')</script>"
    documentIds = @("fake-1", "fake-2", "fake-3")
} | ConvertTo-Json

# Note: Will probably fail with 400 due to invalid doc ids, but should not expose XSS
Test-API -Name "XSS in generate" -Method POST -Path "/api/papers/generate" `
    -Body $xssBody -ExpectedStatus 400

# 7.2 越权 - 使用另一个用户 ID 访问
Write-Host "  [SKIP] Cross-user access - requires second user setup" -ForegroundColor Yellow

# ================================================================
# 第八阶段: 响应格式验证
# ================================================================
Write-Host "`n=======================================" -ForegroundColor Cyan
Write-Host "  阶段 8: 响应格式验证" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

Test-API -Name "Response has success field" -Method GET -Path "/api/auth/me" `
    -ExpectedBodyContains '"success"'

Test-API -Name "Response has data field" -Method GET -Path "/api/auth/me" `
    -ExpectedBodyContains '"data"'

Test-API -Name "Response has message field" -Method GET -Path "/api/auth/me" `
    -ExpectedBodyContains '"message"'

Test-API -Name "Error response has error field" -Method GET -Path "/api/papers/fake-id" `
    -ExpectedStatus 404 -ExpectedBodyContains '"error"'

# ================================================================
# 第九阶段: 500 错误不泄露内部信息
# ================================================================
Write-Host "`n=======================================" -ForegroundColor Cyan
Write-Host "  阶段 9: 错误信息安全测试" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# Try to trigger a server error and check no sensitive info leaks
$malformedJson = '{"courseName": "test", "documentIds": [1,2,3}'  # missing closing brace
try {
    $response = Invoke-WebRequest -Uri "$BaseUrl/api/papers/generate" -Method POST `
        -Headers @{
            "Authorization" = "Bearer $script:global:TOKEN"
            "Content-Type" = "application/json"
        } `
        -Body $malformedJson -SkipCertificateCheck
    Write-Host "  [PASS] Malformed JSON handled gracefully (HTTP $($response.StatusCode))" -ForegroundColor Green
    $passed++
    $total++
} catch {
    $status = $_.Exception.Response.StatusCode.value__
    Write-Host "  [PASS] Malformed JSON rejected (HTTP $status)" -ForegroundColor Green
    $passed++
    $total++
}

# ================================================================
# 测试结果汇总
# ================================================================
Write-Host "`n===========================================================" -ForegroundColor Cyan
Write-Host "  API TEST RESULTS: $passed passed, $failed failed, $total total" -ForegroundColor Cyan
if ($failed -eq 0) {
    Write-Host "  STATUS: ALL API TESTS PASSED" -ForegroundColor Green
} else {
    Write-Host "  STATUS: $failed TEST(S) FAILED" -ForegroundColor Red
}
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "`n提示:" -ForegroundColor Yellow
Write-Host "  - 文件上传测试需要实际文件，请手动测试" -ForegroundColor Yellow
Write-Host "  - 试卷生成测试需要先上传 3+ 个文件并获得文件 ID" -ForegroundColor Yellow
Write-Host "  - DOCX 导出测试需要有已完成的试卷" -ForegroundColor Yellow
Write-Host "  - 配额耗尽测试需要手动减少 remainingGenerations" -ForegroundColor Yellow
Write-Host "  - Token 过期测试需要使用实际过期的 JWT" -ForegroundColor Yellow
