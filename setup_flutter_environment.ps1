# PowerShell script to set up Flutter development environment for mobile trading app

# Configuration
$flutterSdkUrl = "https://storage.googleapis.com/flutter_infra_release/releases/stable/windows/flutter_windows_3.19.3-stable.zip"
$flutterZipFile = "$env:TEMP\flutter_windows.zip"
$flutterInstallPath = "C:\flutter"
$projectPath = "$PSScriptRoot\mobile_app"

# Create directory for Flutter SDK
Write-Host "Creating Flutter SDK directory at $flutterInstallPath..." -ForegroundColor Cyan
if (!(Test-Path $flutterInstallPath)) {
    New-Item -ItemType Directory -Path $flutterInstallPath -Force | Out-Null
}

# Download Flutter SDK
Write-Host "Downloading Flutter SDK..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $flutterSdkUrl -OutFile $flutterZipFile

# Extract Flutter SDK
Write-Host "Extracting Flutter SDK..." -ForegroundColor Cyan
Expand-Archive -Path $flutterZipFile -DestinationPath "C:\" -Force

# Add Flutter to PATH environment variable
Write-Host "Adding Flutter to PATH..." -ForegroundColor Cyan
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $currentPath.Contains($flutterInstallPath + "\bin")) {
    [Environment]::SetEnvironmentVariable("Path", $currentPath + ";" + $flutterInstallPath + "\bin", "User")
    $env:Path = $env:Path + ";" + $flutterInstallPath + "\bin"
}

# Run flutter doctor to verify installation
Write-Host "Running flutter doctor to verify installation..." -ForegroundColor Cyan
flutter doctor -v

# Create Flutter project
Write-Host "Creating Flutter project for the mobile trading app..." -ForegroundColor Cyan
if (!(Test-Path $projectPath)) {
    flutter create --org com.tradingbot --project-name mobile_trading_app $projectPath
}

# Navigate to project directory
Set-Location $projectPath

# Update pubspec.yaml with required dependencies
Write-Host "Updating project dependencies..." -ForegroundColor Cyan
$pubspecPath = "$projectPath\pubspec.yaml"
$pubspec = Get-Content $pubspecPath -Raw
$dependenciesSection = @"
dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.5
  
  # State Management
  flutter_bloc: ^8.1.3
  equatable: ^2.0.5
  
  # Networking
  dio: ^5.3.2
  web_socket_channel: ^2.4.0
  connectivity_plus: ^4.0.2
  
  # Storage & Security
  flutter_secure_storage: ^9.0.0
  hive: ^2.2.3
  hive_flutter: ^1.1.0
  
  # UI Components
  syncfusion_flutter_charts: ^22.2.12
  fl_chart: ^0.63.0
  flutter_svg: ^2.0.7
  shimmer: ^3.0.0
  cached_network_image: ^3.2.3
  
  # Utilities
  intl: ^0.18.1
  logger: ^2.0.1
  path_provider: ^2.1.1
  package_info_plus: ^4.1.0
  device_info_plus: ^9.0.3
  permission_handler: ^10.4.3
"@

$pubspec = $pubspec -replace "(?s)dependencies:.*?dev_dependencies:", "$dependenciesSection`n`ndev_dependencies:"
Set-Content -Path $pubspecPath -Value $pubspec

# Update AndroidManifest.xml to add required permissions
Write-Host "Adding required permissions to AndroidManifest.xml..." -ForegroundColor Cyan
$androidManifestPath = "$projectPath\android\app\src\main\AndroidManifest.xml"
$manifest = Get-Content $androidManifestPath -Raw
$permissionsToAdd = @"
    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
"@

$manifest = $manifest -replace "<manifest(?:[^>]*)>", "<manifest`$1>`n$permissionsToAdd"
Set-Content -Path $androidManifestPath -Value $manifest

# Create directory structure for the app
Write-Host "Creating app directory structure..." -ForegroundColor Cyan
$dirsToCreate = @(
    "$projectPath\lib\config",
    "$projectPath\lib\models",
    "$projectPath\lib\services",
    "$projectPath\lib\blocs",
    "$projectPath\lib\screens\auth",
    "$projectPath\lib\screens\dashboard",
    "$projectPath\lib\screens\trading",
    "$projectPath\lib\screens\market",
    "$projectPath\lib\screens\assets",
    "$projectPath\lib\screens\settings",
    "$projectPath\lib\widgets\cards",
    "$projectPath\lib\widgets\charts",
    "$projectPath\lib\widgets\shared",
    "$projectPath\lib\utils"
)

foreach ($dir in $dirsToCreate) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

Write-Host "Flutter environment setup complete!" -ForegroundColor Green
Write-Host "Project created at $projectPath" -ForegroundColor Green
Write-Host "To run your app, navigate to $projectPath and run 'flutter run'" -ForegroundColor Green
