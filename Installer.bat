# ==============================================================================
# APPLICATION INSTALLER SCRIPT
# ==============================================================================
# 
# WHAT THIS SCRIPT DOES:
# This script automatically installs and configures everything needed to run your application:
# 1. WSL2 (Windows Subsystem for Linux) with Debian (lightweight Linux distribution)
# 2. Docker CE inside WSL2 (lightweight container engine, NOT Docker Desktop)
# 3. SearXNG search engine running in a Docker container
# 4. LM Studio GUI for managing local language models
# 5. Python 3.10 environment with all required packages
# 6. Easy-to-use launcher scripts
#
# SYSTEM REQUIREMENTS:
# - Windows 10 build 19041+ (Windows 10 version 2004) OR Windows 11
# - Administrator privileges (script will ask for elevation)
# - At least 4GB free disk space
# - Internet connection for downloads
# - CPU with virtualization support (most modern CPUs have this)
#
# HOW TO USE THIS SCRIPT:
# 1. Right-click on this PowerShell script file
# 2. Select "Run with PowerShell" 
# 3. If prompted, click "Yes" to run as Administrator
# 4. Follow the on-screen prompts
# 5. The script may restart your computer - this is normal for WSL2 installation
# 6. After restart, the script will continue automatically
# 7. When prompted, set up your Debian username and password
# 8. Wait for installation to complete
# 9. Use the desktop shortcut created to launch your application
#
# TROUBLESHOOTING:
# - If installation fails, check the log file at: %TEMP%\installer.log
# - If WSL2 installation requires restart, the script will handle this automatically
# - If you encounter issues, you can re-run with specific skip flags (see parameters below)
# - For Docker issues in WSL2, try: wsl --shutdown, then restart the script
#
# CUSTOMIZATION OPTIONS:
# You can run this script with special parameters to skip certain steps:
# - Skip WSL2 installation: .\installer.ps1 -SkipWSL
# - Skip Docker installation: .\installer.ps1 -SkipDocker  
# - Skip LM Studio: .\installer.ps1 -SkipLMStudio
# - Skip Python setup: .\installer.ps1 -SkipPython
# - Force reinstall everything: .\installer.ps1 -Force
# - Enable detailed logging: .\installer.ps1 -Verbose
#
# ==============================================================================

param(
    [switch]$SkipWSL,          # Skip WSL2 installation (use if WSL2 already installed)
    [switch]$SkipDocker,       # Skip Docker CE installation (use if Docker already installed)  
    [switch]$SkipLMStudio,     # Skip LM Studio installation (use if LM Studio already installed)
    [switch]$SkipPython,       # Skip Python setup (use if Python already configured)
    [switch]$Force,            # Force reinstallation of all components
    [switch]$Verbose,          # Enable verbose logging for troubleshooting
    [string]$LogPath = "$env:TEMP\installer.log"  # Location of installation log file
)

# ==============================================================================
# CONFIGURATION SECTION
# ==============================================================================
# 
# IMPORTANT: Modify these variables to customize the installation for your specific application
#

# Your application details
$APP_NAME = "Cadenza's Deep Thinking"                    # CHANGE THIS: Your application name
$APP_VERSION = "1.0.0"                      # CHANGE THIS: Your application version
$APP_DESCRIPTION = "Well, you'll see"    # CHANGE THIS: Brief description of your app

# Python configuration
$PYTHON_VERSION = "3.10.11"                 # Python version to install
$REQUIREMENTS_FILE = "requirements.txt"      # CHANGE THIS: Path to your requirements.txt file

# WSL2 configuration
$DEBIAN_DISTRO = "Debian"                   # Using Debian instead of Ubuntu (lighter weight)
$WSL_USERNAME = ""                          # Leave empty to let user choose during setup

# Download URLs - UPDATE THESE WHEN NEW VERSIONS ARE RELEASED
$LM_STUDIO_URL = "https://releases.lmstudio.ai/windows/latest/LMStudio-Setup.exe"
$PYTHON_URL = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe"

# Installation directories
$INSTALL_DIR = "$env:ProgramFiles\$APP_NAME"           # Main installation directory
$TEMP_DIR = "$env:TEMP\$APP_NAME-installer"           # Temporary files during installation
$DESKTOP_PATH = [Environment]::GetFolderPath("Desktop") # Desktop for shortcuts

# SearXNG configuration
$SEARXNG_PORT = "8888"                      # Port where SearXNG will run (http://localhost:8080)
$SEARXNG_CONTAINER_NAME = "searxng"        # Docker container name for SearXNG

# LM Studio configuration  
$LM_STUDIO_PORT = "1234"                   # Default LM Studio API port

# Colors for console output (makes installation process easier to follow)
$Colors = @{
    Info = "Cyan"
    Success = "Green" 
    Warning = "Yellow"
    Error = "Red"
    Progress = "Magenta"
    Header = "White"
}

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================
# These functions handle logging, progress display, and system checks

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Color = "White"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    # Write to console with color
    Write-Host $logEntry -ForegroundColor $Color
    
    # Write to log file (for troubleshooting)
    Add-Content -Path $LogPath -Value $logEntry -ErrorAction SilentlyContinue
}

function Write-Progress-Step {
    param(
        [string]$Step,
        [int]$Current,
        [int]$Total
    )
    
    $percent = [math]::Round(($Current / $Total) * 100)
    Write-Progress -Activity "Installing $APP_NAME" -Status $Step -PercentComplete $percent
    Write-Log "Step $Current/$Total : $Step" -Level "PROGRESS" -Color $Colors.Progress
}

function Write-Header {
    param([string]$Title)
    
    $border = "=" * 80
    Write-Host ""
    Write-Host $border -ForegroundColor $Colors.Header
    Write-Host $Title.ToUpper().PadLeft(($border.Length + $Title.Length) / 2) -ForegroundColor $Colors.Header
    Write-Host $border -ForegroundColor $Colors.Header
    Write-Host ""
}

function Test-AdminPrivileges {
    # Check if the script is running with Administrator privileges
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Request-AdminPrivileges {
    # Restart the script with Administrator privileges if needed
    if (-not (Test-AdminPrivileges)) {
        Write-Log "Administrator privileges required. Restarting script as Administrator..." -Color $Colors.Warning
        
        # Prepare arguments to pass to elevated process
        $arguments = ""
        if ($SkipWSL) { $arguments += " -SkipWSL" }
        if ($SkipDocker) { $arguments += " -SkipDocker" }
        if ($SkipLMStudio) { $arguments += " -SkipLMStudio" }
        if ($SkipPython) { $arguments += " -SkipPython" }
        if ($Force) { $arguments += " -Force" }
        if ($Verbose) { $arguments += " -Verbose" }
        if ($LogPath -ne "$env:TEMP\installer.log") { $arguments += " -LogPath `"$LogPath`"" }
        
        # Start elevated process
        Start-Process -FilePath "powershell.exe" -ArgumentList "-ExecutionPolicy Bypass -File `"$PSCommandPath`"$arguments" -Verb RunAs
        exit 0
    }
}

function Test-WindowsVersion {
    # Check if Windows version is compatible with WSL2
    $version = [System.Environment]::OSVersion.Version
    $buildNumber = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion").CurrentBuild
    
    Write-Log "Detected Windows version: $($version.Major).$($version.Minor) Build $buildNumber" -Color $Colors.Info
    
    # WSL2 requires Windows 10 build 19041 (version 2004) or higher
    if ($buildNumber -lt 19041) {
        Write-Log "ERROR: Windows 10 build 19041 (version 2004) or higher is required for WSL2" -Level "ERROR" -Color $Colors.Error
        Write-Log "Your current build is $buildNumber. Please update Windows and try again." -Level "ERROR" -Color $Colors.Error
        return $false
    }
    
    Write-Log "Windows version is compatible with WSL2" -Color $Colors.Success
    return $true
}

function Test-SystemRequirements {
    # Check all system requirements before starting installation
    Write-Header "CHECKING SYSTEM REQUIREMENTS"
    
    $allChecksPassed = $true
    
    # Check Windows version
    if (-not (Test-WindowsVersion)) {
        $allChecksPassed = $false
    }
    
    # Check available disk space (4GB minimum)
    $freeSpace = [math]::Round((Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'").FreeSpace / 1GB, 2)
    Write-Log "Available disk space: $freeSpace GB" -Color $Colors.Info
    
    if ($freeSpace -lt 4) {
        Write-Log "ERROR: At least 4GB of free disk space is required" -Level "ERROR" -Color $Colors.Error
        $allChecksPassed = $false
    } else {
        Write-Log "Sufficient disk space available" -Color $Colors.Success
    }
    
    # Check for virtualization support
    try {
        $cpu = Get-WmiObject -Class Win32_Processor
        $vmxSupport = $cpu.VirtualizationFirmwareEnabled
        
        if ($vmxSupport) {
            Write-Log "CPU virtualization support detected" -Color $Colors.Success
        } else {
            Write-Log "WARNING: CPU virtualization support may not be enabled in BIOS" -Level "WARNING" -Color $Colors.Warning
            Write-Log "If installation fails, please enable virtualization in your BIOS settings" -Color $Colors.Warning
        }
    } catch {
        Write-Log "Could not detect virtualization support" -Level "WARNING" -Color $Colors.Warning
    }
    
    # Check internet connectivity
    try {
        $testConnection = Test-NetConnection -ComputerName "google.com" -Port 80 -InformationLevel Quiet -WarningAction SilentlyContinue
        if ($testConnection) {
            Write-Log "Internet connectivity confirmed" -Color $Colors.Success
        } else {
            Write-Log "ERROR: Internet connection required for downloads" -Level "ERROR" -Color $Colors.Error
            $allChecksPassed = $false
        }
    } catch {
        Write-Log "WARNING: Could not verify internet connectivity" -Level "WARNING" -Color $Colors.Warning
    }
    
    return $allChecksPassed
}

function Create-TempDirectory {
    # Create temporary directory for downloads and temporary files
    if (Test-Path $TEMP_DIR) {
        if ($Force) {
            Remove-Item $TEMP_DIR -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    
    if (-not (Test-Path $TEMP_DIR)) {
        New-Item -ItemType Directory -Path $TEMP_DIR -Force | Out-Null
        Write-Log "Created temporary directory: $TEMP_DIR" -Color $Colors.Info
    }
}

function Download-File {
    param(
        [string]$Url,
        [string]$OutputPath,
        [string]$Description = "file"
    )
    
    Write-Log "Downloading $Description..." -Color $Colors.Info
    Write-Log "URL: $Url" -Color $Colors.Info
    Write-Log "Destination: $OutputPath" -Color $Colors.Info
    
    try {
        # Try using BITS transfer first (more reliable for large files)
        if (Get-Command Start-BitsTransfer -ErrorAction SilentlyContinue) {
            Start-BitsTransfer -Source $Url -Destination $OutputPath -Description "Downloading $Description" -ErrorAction Stop
        } else {
            # Fallback to Invoke-WebRequest
            $progressPreference = 'SilentlyContinue'  # Hide progress bar for cleaner output
            Invoke-WebRequest -Uri $Url -OutFile $OutputPath -UseBasicParsing -ErrorAction Stop
            $progressPreference = 'Continue'
        }
        
        if (Test-Path $OutputPath) {
            $fileSize = [math]::Round((Get-Item $OutputPath).Length / 1MB, 2)
            Write-Log "Successfully downloaded $Description ($fileSize MB)" -Color $Colors.Success
            return $true
        }
    } catch {
        Write-Log "Failed to download ${Description}: $($_.Exception.Message)" -Level "ERROR" -Color $Colors.Error
        return $false
    }
    
    return $false
}

# ==============================================================================
# WSL2 INSTALLATION FUNCTIONS
# ==============================================================================

function Test-WSLInstalled {
    # Check if WSL2 is already installed and working
    try {
        $wslVersion = wsl --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Log "WSL2 is already installed" -Color $Colors.Success
            
            # Check if Debian is installed
            $distributions = wsl -l -q 2>$null
            if ($distributions -match $DEBIAN_DISTRO) {
                Write-Log "Debian distribution is already installed" -Color $Colors.Success
                return $true
            } else {
                Write-Log "WSL2 installed but Debian distribution not found" -Color $Colors.Warning
                return $false
            }
        }
    } catch {
        # WSL command not found or not working
    }
    
    Write-Log "WSL2 is not installed or not working properly" -Color $Colors.Info
    return $false
}

function Install-WSL {
    Write-Header "INSTALLING WSL2 WITH DEBIAN"
    
    Write-Log "Installing WSL2 with Debian distribution..." -Color $Colors.Info
    Write-Log "This may take several minutes and might require a system restart" -Color $Colors.Warning
    
    try {
        # Install WSL2 with Debian distribution
        # This enables WSL2, Virtual Machine Platform, and installs Debian
        Write-Log "Running: wsl --install -d $DEBIAN_DISTRO" -Color $Colors.Info
        $process = Start-Process -FilePath "wsl" -ArgumentList "--install", "-d", $DEBIAN_DISTRO -Wait -PassThru -NoNewWindow
        
        if ($process.ExitCode -eq 0) {
            Write-Log "WSL2 installation command completed successfully" -Color $Colors.Success
            
            # Check if system restart is required
            $restartRequired = Test-RestartRequired
            
            if ($restartRequired) {
                Write-Log "IMPORTANT: System restart is required to complete WSL2 installation" -Level "WARNING" -Color $Colors.Warning
                
                # Create continuation script that will run after restart
                Create-PostRestartScript
                
                Write-Log "The system will restart in 15 seconds..." -Color $Colors.Warning
                Write-Log "After restart, Debian setup will launch automatically" -Color $Colors.Info
                Write-Log "Please complete the Debian user setup, then run this installer again with -SkipWSL flag" -Color $Colors.Info
                
                # Countdown
                for ($i = 15; $i -gt 0; $i--) {
                    Write-Host "Restarting in $i seconds... (Press Ctrl+C to cancel)" -ForegroundColor $Colors.Warning
                    Start-Sleep -Seconds 1
                }
                
                Restart-Computer -Force
                exit 0
            } else {
                Write-Log "No restart required, continuing with WSL2 setup..." -Color $Colors.Success
                return Wait-ForWSL
            }
        } else {
            Write-Log "WSL2 installation failed with exit code: $($process.ExitCode)" -Level "ERROR" -Color $Colors.Error
            return $false
        }
    } catch {
        Write-Log "WSL2 installation failed: $($_.Exception.Message)" -Level "ERROR" -Color $Colors.Error
        return $false
    }
}

function Test-RestartRequired {
    # Check if system restart is required for WSL2 installation
    
    # Method 1: Check pending reboot registry keys
    $pendingReboot = $false
    
    try {
        $rebootKeys = @(
            "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired",
            "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending",
            "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\PendingFileRenameOperations"
        )
        
        foreach ($key in $rebootKeys) {
            if (Test-Path $key) {
                $pendingReboot = $true
                break
            }
        }
    } catch {
        # Registry check failed, assume restart may be needed
        $pendingReboot = $true
    }
    
    # Method 2: Check Windows features state
    try {
        $wslFeature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -ErrorAction SilentlyContinue
        $vmFeature = Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -ErrorAction SilentlyContinue
        
        if ($wslFeature.State -ne "Enabled" -or $vmFeature.State -ne "Enabled") {
            $pendingReboot = $true
        }
    } catch {
        # Feature check failed, assume restart may be needed
        $pendingReboot = $true
    }
    
    return $pendingReboot
}

function Create-PostRestartScript {
    # Create a script that will run after system restart to continue WSL2 setup
    
    $postRestartScript = @"
# Post-Restart WSL2 Setup Script
# This script runs automatically after Windows restart to complete WSL2 setup

Write-Host "=============================================================================" -ForegroundColor White
Write-Host "WSL2 POST-RESTART SETUP" -ForegroundColor White  
Write-Host "=============================================================================" -ForegroundColor White
Write-Host ""

Write-Host "Continuing WSL2 setup after system restart..." -ForegroundColor Green
Write-Host "Please wait while WSL2 services initialize..." -ForegroundColor Yellow

# Wait for WSL2 service to be ready
`$maxAttempts = 60
`$attempt = 0

do {
    `$attempt++
    Write-Host "Checking WSL2 status (attempt `$attempt/`$maxAttempts)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    try {
        `$wslStatus = wsl --status 2>`$null
        if (`$LASTEXITCODE -eq 0) {
            Write-Host "WSL2 is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if (`$attempt -ge `$maxAttempts) {
        Write-Host "WSL2 setup timeout. Please restart and try again." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} while (`$true)

# Launch Debian for initial user setup
Write-Host ""
Write-Host "=============================================================================" -ForegroundColor White
Write-Host "DEBIAN USER SETUP" -ForegroundColor White
Write-Host "=============================================================================" -ForegroundColor White
Write-Host ""
Write-Host "A Debian terminal will now open for initial user setup." -ForegroundColor Cyan
Write-Host "Please follow these steps:" -ForegroundColor Cyan
Write-Host "1. Choose a username (lowercase, no spaces)" -ForegroundColor White
Write-Host "2. Choose a password (you'll need to type it twice)" -ForegroundColor White
Write-Host "3. Wait for setup to complete" -ForegroundColor White
Write-Host "4. Close the Debian terminal when setup is finished" -ForegroundColor White
Write-Host ""
Write-Host "Press Enter to open Debian setup..." -ForegroundColor Yellow
Read-Host

# Launch Debian setup
wsl -d $DEBIAN_DISTRO

Write-Host ""
Write-Host "=============================================================================" -ForegroundColor White
Write-Host "NEXT STEPS" -ForegroundColor White
Write-Host "=============================================================================" -ForegroundColor White
Write-Host ""
Write-Host "Debian setup is complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To continue the installation, please:" -ForegroundColor Cyan
Write-Host "1. Run the installer script again" -ForegroundColor White
Write-Host "2. Add the -SkipWSL parameter like this:" -ForegroundColor White
Write-Host "   .\installer.ps1 -SkipWSL" -ForegroundColor Yellow
Write-Host ""
Write-Host "This will skip the WSL2 installation and continue with Docker and other components." -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to close this window"
"@
    
    $postRestartScriptPath = "$env:TEMP\wsl-post-restart.ps1"
    $postRestartScript | Out-File -FilePath $postRestartScriptPath -Encoding UTF8
    
    # Create a batch file to run the PowerShell script (easier for RunOnce)
    $batchScript = @"
@echo off
powershell.exe -ExecutionPolicy Bypass -File "$postRestartScriptPath"
"@
    
    $batchScriptPath = "$env:TEMP\wsl-post-restart.bat"
    $batchScript | Out-File -FilePath $batchScriptPath -Encoding ASCII
    
    # Set up RunOnce registry entry to run after restart
    try {
        $runOnceKey = "HKLM:\Software\Microsoft\Windows\CurrentVersion\RunOnce"
        Set-ItemProperty -Path $runOnceKey -Name "WSLPostRestart" -Value "`"$batchScriptPath`"" -ErrorAction Stop
        Write-Log "Post-restart script configured successfully" -Color $Colors.Success
    } catch {
        Write-Log "Warning: Could not configure post-restart script: $($_.Exception.Message)" -Level "WARNING" -Color $Colors.Warning
    }
}

function Wait-ForWSL {
    # Wait for WSL2 to be fully operational and test Debian
    Write-Log "Waiting for WSL2 to be fully operational..." -Color $Colors.Info
    
    $maxAttempts = 30
    $attempt = 0
    
    do {
        $attempt++
        Write-Log "Testing WSL2 connection (attempt $attempt/$maxAttempts)..." -Color $Colors.Info
        Start-Sleep -Seconds 5
        
        try {
            # Test basic WSL functionality
            $testResult = wsl -d $DEBIAN_DISTRO echo "WSL2 test successful" 2>$null
            if ($LASTEXITCODE -eq 0 -and $testResult -eq "WSL2 test successful") {
                Write-Log "WSL2 with Debian is fully operational" -Color $Colors.Success
                return $true
            }
        } catch {
            # Continue waiting
        }
        
        if ($attempt -ge $maxAttempts) {
            Write-Log "WSL2 setup timeout. Please check WSL2 installation manually." -Level "ERROR" -Color $Colors.Error
            Write-Log "You can test WSL2 by running: wsl -d $DEBIAN_DISTRO" -Color $Colors.Info
            return $false
        }
    } while ($true)
}

# ==============================================================================
# DOCKER CE INSTALLATION FUNCTIONS
# ==============================================================================

function Test-DockerInstalled {
    # Check if Docker CE is installed in WSL2
    try {
        $dockerVersion = wsl -d $DEBIAN_DISTRO docker --version 2>$null
        if ($LASTEXITCODE -eq 0 -and $dockerVersion -match "Docker version") {
            Write-Log "Docker CE is already installed in WSL2: $dockerVersion" -Color $Colors.Success
            
            # Test if Docker daemon is running
            $dockerInfo = wsl -d $DEBIAN_DISTRO docker info 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Log "Docker daemon is running" -Color $Colors.Success
                return $true
            } else {
                Write-Log "Docker is installed but daemon is not running" -Color $Colors.Warning
                return $false
            }
        }
    } catch {
        # Docker not found or not working
    }
    
    Write-Log "Docker CE is not installed in WSL2" -Color $Colors.Info
    return $false
}

function Install-Docker {
    Write-Header "INSTALLING DOCKER CE IN WSL2"
    
    Write-Log "Installing Docker CE in Debian WSL2..." -Color $Colors.Info
    Write-Log "This process will take several minutes" -Color $Colors.Info
    
    # Create Docker installation script for WSL2
    $dockerInstallScript = @"
#!/bin/bash

# Docker CE Installation Script for Debian in WSL2
# This script installs Docker CE (Community Edition) - the lightweight version

echo "============================================================================="
echo "DOCKER CE INSTALLATION IN DEBIAN WSL2"
echo "============================================================================="
echo ""

# Exit on any error
set -e

# Update package database
echo "Updating package database..."
sudo apt-get update -qq

# Install prerequisites
echo "Installing prerequisites..."
sudo apt-get install -y -qq \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    apt-transport-https \
    software-properties-common

# Add Docker's official GPG key
echo "Adding Docker GPG key..."
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes

# Set up Docker repository
echo "Setting up Docker repository..."
echo "deb [arch=`$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian `$(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package database with Docker packages
echo "Updating package database with Docker packages..."
sudo apt-get update -qq

# Install Docker CE
echo "Installing Docker CE..."
sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add current user to docker group (allows running docker without sudo)
echo "Adding user to docker group..."
sudo usermod -aG docker `$USER

# Configure Docker to start automatically
echo "Configuring Docker service..."
sudo systemctl enable docker 2>/dev/null || true

# Start Docker service
echo "Starting Docker service..."
sudo service docker start

# Test Docker installation
echo "Testing Docker installation..."
if sudo docker run --rm hello-world > /dev/null 2>&1; then
    echo "Docker CE installation successful!"
    echo ""
    echo "Docker version:"
    docker --version
    echo ""
    echo "To use Docker without sudo, please restart your WSL2 session or run:"
    echo "newgrp docker"
else
    echo "Docker installation may have issues. Please check manually."
    exit 1
fi

echo ""
echo "Docker CE installation completed successfully!"
"@
    
    # Write the script to a temporary file
    $dockerScriptPath = "$TEMP_DIR\install-docker.sh"
    $dockerInstallScript | Out-File -FilePath $dockerScriptPath -Encoding UTF8
    
    try {
        # Copy script to WSL2 and make it executable
        Write-Log "Copying Docker installation script to WSL2..." -Color $Colors.Info
        wsl -d $DEBIAN_DISTRO -- mkdir -p /tmp/installer 2>$null
        
        # Convert Windows path to WSL path and copy
        $wslScriptPath = "/tmp/installer/install-docker.sh"
        wsl -d $DEBIAN_DISTRO -- cp "/mnt/c$(($dockerScriptPath -replace '^C:', '' -replace '\\', '/'))" $wslScriptPath 2>$null
        
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to copy script to WSL2"
        }
        
        # Make script executable and run it
        Write-Log "Running Docker installation script in WSL2..." -Color $Colors.Info
        Write-Log "This will take several minutes. Please be patient..." -Color $Colors.Warning
        
        wsl -d $DEBIAN_DISTRO -- chmod +x $wslScriptPath
        wsl -d $DEBIAN_DISTRO -- bash $wslScriptPath
        
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Docker CE installation completed successfully" -Color $Colors.Success
            
            # Wait a moment for Docker to fully initialize
            Start-Sleep -Seconds 5
            
            # Test Docker installation
            return Test-DockerWorking
        } else {
            Write-Log "Docker installation script failed with exit code: $LASTEXITCODE" -Level "ERROR" -Color $Colors.Error
            return $false
        }
    } catch {
        Write-Log "Docker installation failed: $($_.Exception.Message)" -Level "ERROR" -Color $Colors.Error
        return $false
    }
}

function Test-DockerWorking {
    # Test if Docker is working properly in WSL2
    Write-Log "Testing Docker functionality..." -Color $Colors.Info
    
    try {
        # Test Docker daemon
        $dockerInfo = wsl -d $DEBIAN_DISTRO docker info 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Log "Starting Docker daemon..." -Color $Colors.Info
            wsl -d $DEBIAN_DISTRO sudo service docker start 2>$null
            Start-Sleep -Seconds 5
        }
        
        # Test Docker with hello-world
        $dockerTest = wsl -d $DEBIAN_DISTRO docker run --rm hello-world 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Docker is working correctly" -Color $Colors.Success
            return $true
        } else {
            Write-Log "Docker test failed" -Level "ERROR" -Color $Colors.Error
            return $false
        }
    } catch {
        Write-Log "Docker test failed: $($_.Exception.Message)" -Level "ERROR" -Color $Colors.Error
        return $false
    }
}

# ==============================================================================
# SEARXNG INSTALLATION FUNCTIONS
# ==============================================================================

function Test-SearXNGInstalled {
    # Check if SearXNG container is already running
    try {
        $containerStatus = wsl -d $DEBIAN_DISTRO docker ps --filter "name=$SEARXNG_CONTAINER_NAME" --format "{{.Status}}" 2>$null
        if ($LASTEXITCODE -eq 0 -and $containerStatus -match "Up") {
            Write-Log "SearXNG container is already running" -Color $Colors.Success
            return $true
        }
        
        # Check if container exists but is stopped
        $containerExists = wsl -d $DEBIAN_DISTRO docker ps -a --filter "name=$SEARXNG_CONTAINER_NAME" --format "{{.Names}}" 2>$null
        if ($LASTEXITCODE -eq 0 -and $containerExists -eq $SEARXNG_CONTAINER_NAME) {
            Write-Log "SearXNG container exists but is not running" -Color $Colors.Info
            return $false
        }
    } catch {
        # Container check failed
    }
    
    Write-Log "SearXNG container is not installed" -Color $Colors.Info
    return $false
}

function Install-SearXNG {
    Write-Header "INSTALLING SEARXNG SEARCH ENGINE"
    
    Write-Log "Setting up SearXNG in Docker container..." -Color $Colors.Info
    Write-Log "SearXNG will be accessible at: http://localhost:$SEARXNG_PORT" -Color $Colors.Info
    
    try {
        # Ensure Docker is running
        Write-Log "Ensuring Docker daemon is running..." -Color $Colors.Info
        wsl -d $DEBIAN_DISTRO sudo service docker start 2>$null
        Start-Sleep -Seconds 3
        
        # Pull SearXNG image
        Write-Log "Downloading SearXNG Docker image..." -Color $Colors.Info
        Write-Log "This may take a few minutes for the first download..." -Color $Colors.Warning
        
        wsl -d $DEBIAN_DISTRO docker pull searxng/searxng
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to pull SearXNG Docker image"
        }
        
        Write-Log "SearXNG image downloaded successfully" -Color $Colors.Success
        
        # Remove existing container if it exists
        Write-Log "Removing any existing SearXNG container..." -Color $Colors.Info
        wsl -d $DEBIAN_DISTRO docker rm -f $SEARXNG_CONTAINER_NAME 2>$null
        
        # Create and start SearXNG container
        Write-Log "Creating SearXNG container..." -Color $Colors.Info
        
        $dockerRunCommand = @"
docker run -d \
  --name $SEARXNG_CONTAINER_NAME \
  --restart unless-stopped \
  -p ${SEARXNG_PORT}:8080 \
  -v searxng-config:/etc/searxng \
  searxng/searxng
"@
        
        wsl -d $DEBIAN_DISTRO -- bash -c $dockerRunCommand
        
        if ($LASTEXITCODE -eq 0) {
            Write-Log "SearXNG container created successfully" -Color $Colors.Success
            
            # Wait for SearXNG to start up
            Write-Log "Waiting for SearXNG to start up..." -Color $Colors.Info
            Start-Sleep -Seconds 10
            
            # Test SearXNG accessibility
            return Test-SearXNGWorking
        } else {
            throw "Failed to create SearXNG container"
        }
    } catch {
        Write-Log "SearXNG installation failed: $($_.Exception.Message)" -Level "ERROR" -Color $Colors.Error
        return $false
    }
}

function Test-SearXNGWorking {
    # Test if SearXNG is accessible and working
    Write-Log "Testing SearXNG accessibility..." -Color $Colors.Info
    
    $maxAttempts = 12  # 2 minutes total (12 * 10 seconds)
    $attempt = 0
    
    do {
        $attempt++
        Write-Log "Testing SearXNG connection (attempt $attempt/$maxAttempts)..." -Color $Colors.Info
        
        try {
            # Test connection to SearXNG
            $response = Invoke-WebRequest -Uri "http://localhost:$SEARXNG_PORT" -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
            
            if ($response.StatusCode -eq 200 -and $response.Content -match "SearXNG") {
                Write-Log "SearXNG is accessible and working at http://localhost:$SEARXNG_PORT" -Color $Colors.Success
                return $true
            }
        } catch {
            if ($attempt -lt $maxAttempts) {
                Write-Log "SearXNG not ready yet, waiting 10 seconds..." -Color $Colors.Warning
                Start-Sleep -Seconds 10
            }
        }
        
        if ($attempt -ge $maxAttempts) {
            Write-Log "SearXNG accessibility test timeout" -Level "ERROR" -Color $Colors.Error
            Write-Log "Please check if SearXNG container is running: wsl -d $DEBIAN_DISTRO docker ps" -Color $Colors.Info
            return $false
        }
    } while ($true)
}

# ==============================================================================
# LM STUDIO INSTALLATION FUNCTIONS  
# ==============================================================================

function Test-LMStudioInstalled {
    # Check if LM Studio is already installed
    $lmStudioPaths = @(
        "$env:LOCALAPPDATA\Programs\LMStudio\LM Studio.exe",
        "$env:PROGRAMFILES\LM Studio\LM Studio.exe",
        "$env:PROGRAMFILES(X86)\LM Studio\LM Studio.exe"
    )
    
    foreach ($path in $lmStudioPaths) {
        if (Test-Path $path) {
            Write-Log "LM Studio found at: $path" -Color $Colors.Success
            return $true
        }
    }
    
    Write-Log "LM Studio is not installed" -Color $Colors.Info
    return $false
}

function Install-LMStudio {
    Write-Header "INSTALLING LM STUDIO"
    
    Write-Log "Downloading and installing LM Studio GUI..." -Color $Colors.Info
    Write-Log "LM Studio provides an easy interface for managing local language models" -Color $Colors.Info
    
    try {
        # Download LM Studio installer
        $lmStudioInstaller = "$TEMP_DIR\LMStudio-Setup.exe"
        
        if (-not (Download-File -Url $LM_STUDIO_URL -OutputPath $lmStudioInstaller -Description "LM Studio installer")) {
            throw "Failed to download LM Studio installer"
        }
        
        # Install LM Studio silently
        Write-Log "Installing LM Studio..." -Color $Colors.Info
        Write-Log "This may take a few minutes..." -Color $Colors.Warning
        
        $installProcess = Start-Process -FilePath $lmStudioInstaller -ArgumentList "/S" -Wait -PassThru -NoNewWindow
        
        if ($installProcess.ExitCode -eq 0) {
            Write-Log "LM Studio installed successfully" -Color $Colors.Success
            
            # Wait a moment for installation to complete
            Start-Sleep -Seconds 5
            
            # Verify installation
            if (Test-LMStudioInstalled) {
                Write-Log "LM Studio installation verified" -Color $Colors.Success
                return $true
            } else {
                Write-Log "LM Studio installation could not be verified" -Level "WARNING" -Color $Colors.Warning
                return $false
            }
        } else {
            throw "LM Studio installer failed with exit code: $($installProcess.ExitCode)"
        }
    } catch {
        Write-Log "LM Studio installation failed: $($_.Exception.Message)" -Level "ERROR" -Color $Colors.Error
        return $false
    }
}

# ==============================================================================
# PYTHON INSTALLATION FUNCTIONS
# ==============================================================================

function Test-PythonInstalled {
    # Check if Python 3.10 is installed and accessible
    try {
        $pythonVersion = python --version 2>$null
        if ($LASTEXITCODE -eq 0 -and $pythonVersion -match "Python 3\.10") {
            Write-Log "Python 3.10 is already installed: $pythonVersion" -Color $Colors.Success
            return $true
        }
        
        # Also check py launcher
        $pyVersion = py -3.10 --version 2>$null
        if ($LASTEXITCODE -eq 0 -and $pyVersion -match "Python 3\.10") {
            Write-Log "Python 3.10 is available via py launcher: $pyVersion" -Color $Colors.Success
            return $true
        }
    } catch {
        # Python not found or not working
    }
    
    Write-Log "Python 3.10 is not installed or not accessible" -Color $Colors.Info
    return $false
}

function Install-Python {
    Write-Header "INSTALLING PYTHON 3.10"
    
    Write-Log "Downloading and installing Python $PYTHON_VERSION..." -Color $Colors.Info
    
    try {
        # Download Python installer
        $pythonInstaller = "$TEMP_DIR\python-$PYTHON_VERSION-installer.exe"
        
        if (-not (Download-File -Url $PYTHON_URL -OutputPath $pythonInstaller -Description "Python $PYTHON_VERSION installer")) {
            throw "Failed to download Python installer"
        }
        
        # Install Python with specific options
        Write-Log "Installing Python $PYTHON_VERSION..." -Color $Colors.Info
        Write-Log "This installation includes pip and adds Python to PATH" -Color $Colors.Info
        
        $pythonInstallArgs = @(
            "/quiet",                    # Silent installation
            "InstallAllUsers=0",         # Install for current user only
            "PrependPath=1",             # Add Python to PATH
            "Include_test=0",            # Don't include test suite
            "Include_doc=0",             # Don't include documentation
            "Include_dev=1",             # Include development headers
            "Include_pip=1",             # Include pip
            "Include_tcltk=0"            # Don't include Tkinter (saves space)
        )
        
        $installProcess = Start-Process -FilePath $pythonInstaller -ArgumentList $pythonInstallArgs -Wait -PassThru -NoNewWindow
        
        if ($installProcess.ExitCode -eq 0) {
            Write-Log "Python installation completed" -Color $Colors.Success
            
            # Refresh environment variables
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            
            # Wait a moment for installation to complete
            Start-Sleep -Seconds 5
            
            # Verify Python installation
            if (Test-PythonInstalled) {
                Write-Log "Python installation verified" -Color $Colors.Success
                return $true
            } else {
                Write-Log "Python installation could not be verified immediately" -Level "WARNING" -Color $Colors.Warning
                Write-Log "You may need to restart your command prompt or system" -Color $Colors.Warning
                return $false
            }
        } else {
            throw "Python installer failed with exit code: $($installProcess.ExitCode)"
        }
    } catch {
        Write-Log "Python installation failed: $($_.Exception.Message)" -Level "ERROR" -Color $Colors.Error
        return $false
    }
}

function Install-PythonPackages {
    Write-Header "INSTALLING PYTHON PACKAGES"
    
    Write-Log "Installing required Python packages..." -Color $Colors.Info
    
    try {
        # Check if requirements.txt exists
        if (-not (Test-Path $REQUIREMENTS_FILE)) {
            Write-Log "WARNING: requirements.txt file not found at: $REQUIREMENTS_FILE" -Level "WARNING" -Color $Colors.Warning
            Write-Log "Creating a basic requirements.txt with common packages..." -Color $Colors.Info
            
            # Create a basic requirements.txt
            $basicRequirements = @"
# Basic requirements for the application
requests>=2.25.0
beautifulsoup4>=4.9.0
lxml>=4.6.0
python-dotenv>=0.19.0
colorama>=0.4.4
tqdm>=4.62.0
"@
            $basicRequirements | Out-File -FilePath $REQUIREMENTS_FILE -Encoding UTF8
            Write-Log "Basic requirements.txt created" -Color $Colors.Success
        }
        
        # Upgrade pip first
        Write-Log "Upgrading pip..." -Color $Colors.Info
        $pipUpgrade = Start-Process -FilePath "python" -ArgumentList "-m", "pip", "install", "--upgrade", "pip" -Wait -PassThru -NoNewWindow
        
        if ($pipUpgrade.ExitCode -eq 0) {
            Write-Log "Pip upgraded successfully" -Color $Colors.Success
        } else {
            Write-Log "Pip upgrade failed, continuing anyway..." -Level "WARNING" -Color $Colors.Warning
        }
        
        # Install packages from requirements.txt
        Write-Log "Installing packages from requirements.txt..." -Color $Colors.Info
        Write-Log "This may take several minutes depending on the packages..." -Color $Colors.Warning
        
        $pipInstall = Start-Process -FilePath "python" -ArgumentList "-m", "pip", "install", "-r", $REQUIREMENTS_FILE -Wait -PassThru -NoNewWindow
        
        if ($pipInstall.ExitCode -eq 0) {
            Write-Log "Python packages installed successfully" -Color $Colors.Success
            return $true
        } else {
            Write-Log "Some Python packages failed to install (exit code: $($pipInstall.ExitCode))" -Level "WARNING" -Color $Colors.Warning
            Write-Log "You may need to install some packages manually later" -Color $Colors.Warning
            return $false
        }
    } catch {
        Write-Log "Python package installation failed: $($_.Exception.Message)" -Level "ERROR" -Color $Colors.Error
        return $false
    }
}

# ==============================================================================
# LAUNCHER AND SHORTCUT CREATION FUNCTIONS
# ==============================================================================

function Create-LauncherScripts {
    Write-Header "CREATING LAUNCHER SCRIPTS"
    
    Write-Log "Creating easy-to-use launcher scripts..." -Color $Colors.Info
    
    try {
        # Create installation directory
        if (-not (Test-Path $INSTALL_DIR)) {
            New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null
            Write-Log "Created installation directory: $INSTALL_DIR" -Color $Colors.Info
        }
        
        # Create main launcher batch script
        $launcherScript = Create-MainLauncher
        $launcherPath = "$INSTALL_DIR\Launch-$APP_NAME.bat"
        $launcherScript | Out-File -FilePath $launcherPath -Encoding ASCII
        
        # Create PowerShell launcher (more robust)
        $psLauncherScript = Create-PowerShellLauncher
        $psLauncherPath = "$INSTALL_DIR\Launch-$APP_NAME.ps1"
        $psLauncherScript | Out-File -FilePath $psLauncherPath -Encoding UTF8
        
        # Create stop script
        $stopScript = Create-StopScript
        $stopPath = "$INSTALL_DIR\Stop-$APP_NAME.bat"
        $stopScript | Out-File -FilePath $stopPath -Encoding ASCII
        
        # Create desktop shortcuts
        Create-DesktopShortcuts -LauncherPath $launcherPath -StopPath $stopPath
        
        # Create configuration file
        Create-ConfigFile
        
        Write-Log "Launcher scripts created successfully" -Color $Colors.Success
        return $true
    } catch {
        Write-Log "Failed to create launcher scripts: $($_.Exception.Message)" -Level "ERROR" -Color $Colors.Error
        return $false
    }
}

function Create-MainLauncher {
    # Create the main batch launcher script
    return @"
@echo off
REM ============================================================================
REM $APP_NAME LAUNCHER SCRIPT
REM ============================================================================
REM This script starts all components needed for $APP_NAME:
REM 1. Docker daemon in WSL2
REM 2. SearXNG search engine container
REM 3. LM Studio GUI (for model management)
REM 4. Your Python application
REM
REM If you encounter issues, check the log files or run with administrator privileges.
REM ============================================================================

title $APP_NAME Launcher

echo.
echo ============================================================================
echo STARTING $APP_NAME
echo ============================================================================
echo.

REM Change to the installation directory
cd /d "$INSTALL_DIR"

REM Step 1: Start Docker daemon in WSL2
echo [1/4] Starting Docker daemon in WSL2...
wsl -d $DEBIAN_DISTRO sudo service docker start >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Failed to start Docker daemon. WSL2 may not be properly configured.
    echo Please check your WSL2 installation.
    pause
    exit /b 1
)
echo Docker daemon started successfully.

REM Step 2: Start SearXNG container
echo.
echo [2/4] Starting SearXNG search engine...
wsl -d $DEBIAN_DISTRO docker start $SEARXNG_CONTAINER_NAME >nul 2>&1
if %errorlevel% neq 0 (
    echo SearXNG container not found, creating new one...
    wsl -d $DEBIAN_DISTRO docker run -d --name $SEARXNG_CONTAINER_NAME --restart unless-stopped -p ${SEARXNG_PORT}:8080 searxng/searxng >nul 2>&1
    if %errorlevel% neq 0 (
        echo ERROR: Failed to start SearXNG container.
        echo Please check Docker installation in WSL2.
        pause
        exit /b 1
    )
)
echo SearXNG started successfully at http://localhost:$SEARXNG_PORT

REM Step 3: Start LM Studio GUI
echo.
echo [3/4] Starting LM Studio...
set "LMSTUDIO_PATH="
if exist "%LOCALAPPDATA%\Programs\LMStudio\LM Studio.exe" (
    set "LMSTUDIO_PATH=%LOCALAPPDATA%\Programs\LMStudio\LM Studio.exe"
) else if exist "%PROGRAMFILES%\LM Studio\LM Studio.exe" (
    set "LMSTUDIO_PATH=%PROGRAMFILES%\LM Studio\LM Studio.exe"
) else if exist "%PROGRAMFILES(X86)%\LM Studio\LM Studio.exe" (
    set "LMSTUDIO_PATH=%PROGRAMFILES(X86)%\LM Studio\LM Studio.exe"
)

if defined LMSTUDIO_PATH (
    start "" "%LMSTUDIO_PATH%"
    echo LM Studio launched successfully.
) else (
    echo WARNING: LM Studio not found. Please install LM Studio manually.
    echo You can download it from: https://lmstudio.ai/
)

REM Step 4: Wait for services to initialize
echo.
echo [4/4] Waiting for services to initialize...
timeout /t 15 /nobreak >nul

REM Test SearXNG connectivity
echo Testing SearXNG connection...
curl -s http://localhost:$SEARXNG_PORT >nul 2>&1
if %errorlevel% equ 0 (
    echo SearXNG is ready and accessible.
) else (
    echo WARNING: SearXNG may not be fully ready yet.
    echo It may take a few more moments to start up.
)

REM Step 5: Launch the main application
echo.
echo ============================================================================
echo LAUNCHING $APP_NAME APPLICATION
echo ============================================================================
echo.

REM Check if Python script exists
if exist "your_script.py" (
    echo Starting your application...
    python your_script.py
) else (
    echo.
    echo ============================================================================
    echo SETUP COMPLETE
    echo ============================================================================
    echo.
    echo All services are now running:
    echo.
    echo ^> SearXNG Search Engine: http://localhost:$SEARXNG_PORT
    echo ^> LM Studio: Running (check system tray)
    echo ^> LM Studio API: http://localhost:$LM_STUDIO_PORT (when models loaded)
    echo.
    echo To use your application:
    echo 1. Place your Python script in: $INSTALL_DIR
    echo 2. Make sure it's named 'your_script.py' or update this launcher
    echo 3. Ensure your script connects to:
    echo    - SearXNG: http://localhost:$SEARXNG_PORT
    echo    - LM Studio API: http://localhost:$LM_STUDIO_PORT
    echo.
    echo ============================================================================
)

echo.
echo Press any key to exit...
pause >nul
"@
}

function Create-PowerShellLauncher {
    # Create a more robust PowerShell launcher
    return @"
# ============================================================================
# $APP_NAME POWERSHELL LAUNCHER
# ============================================================================
# More robust launcher with better error handling and status checking
# ============================================================================

param(
    [switch]`$Verbose,
    [switch]`$NoWait
)

`$ErrorActionPreference = "Continue"

function Write-Status {
    param([string]`$Message, [string]`$Status = "INFO")
    
    `$color = switch (`$Status) {
        "SUCCESS" { "Green" }
        "WARNING" { "Yellow" }
        "ERROR" { "Red" }
        default { "Cyan" }
    }
    
    `$timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] [`$Status] `$Message" -ForegroundColor `$color
}

function Test-ServiceReady {
    param([string]`$Url, [string]`$ServiceName, [int]`$TimeoutSeconds = 30)
    
    Write-Status "Testing `$ServiceName connectivity..." "INFO"
    
    for (`$i = 1; `$i -le `$TimeoutSeconds; `$i++) {
        try {
            `$response = Invoke-WebRequest -Uri `$Url -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
            if (`$response.StatusCode -eq 200) {
                Write-Status "`$ServiceName is ready and accessible" "SUCCESS"
                return `$true
            }
        } catch {
            if (`$i -eq `$TimeoutSeconds) {
                Write-Status "`$ServiceName is not responding after `$TimeoutSeconds seconds" "WARNING"
                return `$false
            }
            Start-Sleep -Seconds 1
        }
    }
    return `$false
}

# Main execution
try {
    Write-Host ""
    Write-Host "============================================================================" -ForegroundColor White
    Write-Host "$APP_NAME LAUNCHER" -ForegroundColor White
    Write-Host "============================================================================" -ForegroundColor White
    Write-Host ""
    
    # Change to installation directory
    Set-Location "$INSTALL_DIR"
    
    # Step 1: Start Docker daemon
    Write-Status "Starting Docker daemon in WSL2..." "INFO"
    wsl -d $DEBIAN_DISTRO sudo service docker start 2>`$null
    if (`$LASTEXITCODE -ne 0) {
        Write-Status "Failed to start Docker daemon" "ERROR"
        throw "Docker daemon failed to start"
    }
    Write-Status "Docker daemon started successfully" "SUCCESS"
    
    # Step 2: Start SearXNG
    Write-Status "Starting SearXNG container..." "INFO"
    wsl -d $DEBIAN_DISTRO docker start $SEARXNG_CONTAINER_NAME 2>`$null
    if (`$LASTEXITCODE -ne 0) {
        Write-Status "SearXNG container not found, creating new one..." "WARNING"
        wsl -d $DEBIAN_DISTRO docker run -d --name $SEARXNG_CONTAINER_NAME --restart unless-stopped -p ${SEARXNG_PORT}:8080 searxng/searxng 2>`$null
        if (`$LASTEXITCODE -ne 0) {
            Write-Status "Failed to create SearXNG container" "ERROR"
            throw "SearXNG container creation failed"
        }
    }
    Write-Status "SearXNG container started" "SUCCESS"
    
    # Step 3: Start LM Studio
    Write-Status "Launching LM Studio..." "INFO"
    `$lmStudioPaths = @(
        "`$env:LOCALAPPDATA\Programs\LMStudio\LM Studio.exe",
        "`$env:PROGRAMFILES\LM Studio\LM Studio.exe",
        "`$env:PROGRAMFILES(X86)\LM Studio\LM Studio.exe"
    )
    
    `$lmStudioFound = `$false
    foreach (`$path in `$lmStudioPaths) {
        if (Test-Path `$path) {
            Start-Process -FilePath `$path
            Write-Status "LM Studio launched successfully" "SUCCESS"
            `$lmStudioFound = `$true
            break
        }
    }
    
    if (-not `$lmStudioFound) {
        Write-Status "LM Studio not found. Please install from https://lmstudio.ai/" "WARNING"
    }
    
    # Step 4: Wait and test services
    Write-Status "Waiting for services to initialize..." "INFO"
    Start-Sleep -Seconds 10
    
    # Test SearXNG
    Test-ServiceReady -Url "http://localhost:$SEARXNG_PORT" -ServiceName "SearXNG" -TimeoutSeconds 30
    
    # Step 5: Launch application if it exists
    if (Test-Path "your_script.py") {
        Write-Status "Launching your application..." "INFO"
        python your_script.py
    } else {
        Write-Host ""
        Write-Host "============================================================================" -ForegroundColor White
        Write-Host "SETUP COMPLETE - SERVICES RUNNING" -ForegroundColor Green
        Write-Host "============================================================================" -ForegroundColor White
        Write-Host ""
        Write-Host "Services Status:" -ForegroundColor Cyan
        Write-Host "> SearXNG Search Engine: http://localhost:$SEARXNG_PORT" -ForegroundColor White
        Write-Host "> LM Studio: Running (check system tray)" -ForegroundColor White
        Write-Host "> LM Studio API: http://localhost:$LM_STUDIO_PORT (when models loaded)" -ForegroundColor White
        Write-Host ""
        Write-Host "Next Steps:" -ForegroundColor Yellow
        Write-Host "1. Load a model in LM Studio" -ForegroundColor White
        Write-Host "2. Place your Python script as 'your_script.py' in this directory" -ForegroundColor White
        Write-Host "3. Re-run this launcher to start your application" -ForegroundColor White
        Write-Host ""
    }
    
} catch {
    Write-Status "Launcher failed: `$(`$_.Exception.Message)" "ERROR"
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Make sure WSL2 is properly installed" -ForegroundColor White
    Write-Host "2. Check if Docker is working: wsl -d $DEBIAN_DISTRO docker --version" -ForegroundColor White
    Write-Host "3. Check the installation log: $env:TEMP\installer.log" -ForegroundColor White
    Write-Host ""
} finally {
    if (-not `$NoWait) {
        Write-Host "Press any key to exit..." -ForegroundColor Gray
        `$null = `$Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
}
"@
}

function Create-StopScript {
    # Create script to stop all services
    return @"
@echo off
REM ============================================================================
REM $APP_NAME STOP SCRIPT
REM ============================================================================
REM This script stops all components of $APP_NAME
REM ============================================================================

title Stopping $APP_NAME

echo.
echo ============================================================================
echo STOPPING $APP_NAME SERVICES
echo ============================================================================
echo.

echo Stopping SearXNG container...
wsl -d $DEBIAN_DISTRO docker stop $SEARXNG_CONTAINER_NAME >nul 2>&1
if %errorlevel% equ 0 (
    echo SearXNG stopped successfully.
) else (
    echo SearXNG was not running or failed to stop.
)

echo.
echo Stopping Docker daemon in WSL2...
wsl -d $DEBIAN_DISTRO sudo service docker stop >nul 2>&1
if %errorlevel% equ 0 (
    echo Docker daemon stopped successfully.
) else (
    echo Docker daemon was not running or failed to stop.
)

echo.
echo Note: LM Studio needs to be closed manually from the system tray.
echo.
echo All services stopped.
echo.
pause
"@
}

function Create-DesktopShortcuts {
    param(
        [string]$LauncherPath,
        [string]$StopPath
    )
    
    try {
        # Create desktop shortcut for launcher
        $WshShell = New-Object -comObject WScript.Shell
        
        # Main launcher shortcut
        $LauncherShortcut = $WshShell.CreateShortcut("$DESKTOP_PATH\Start $APP_NAME.lnk")
        $LauncherShortcut.TargetPath = $LauncherPath
        $LauncherShortcut.WorkingDirectory = $INSTALL_DIR
        $LauncherShortcut.Description = "Start $APP_NAME with all required services"
        $LauncherShortcut.IconLocation = "shell32.dll,137"  # Green arrow icon
        $LauncherShortcut.Save()
        
        # Stop services shortcut
        $StopShortcut = $WshShell.CreateShortcut("$DESKTOP_PATH\Stop $APP_NAME.lnk")
        $StopShortcut.TargetPath = $StopPath
        $StopShortcut.WorkingDirectory = $INSTALL_DIR
        $StopShortcut.Description = "Stop all $APP_NAME services"
        $StopShortcut.IconLocation = "shell32.dll,131"  # Red X icon
        $StopShortcut.Save()
        
        Write-Log "Desktop shortcuts created successfully" -Color $Colors.Success
        return $true
    } catch {
        Write-Log "Failed to create desktop shortcuts: $($_.Exception.Message)" -Level "WARNING" -Color $Colors.Warning
        return $false
    }
}

function Create-ConfigFile {
    # Create configuration file for the application
    $configContent = @"
# ============================================================================
# $APP_NAME CONFIGURATION FILE
# ============================================================================
# This file contains configuration settings for your application.
# Modify these values as needed for your specific setup.
# ============================================================================

[Services]
# SearXNG search engine configuration
SearXNG_URL=http://localhost:$SEARXNG_PORT
SearXNG_Container=$SEARXNG_CONTAINER_NAME

# LM Studio configuration
LMStudio_API_URL=http://localhost:$LM_STUDIO_PORT
LMStudio_API_Key=

[WSL2]
# WSL2 distribution name
Distribution=$DEBIAN_DISTRO

[Application]
# Your application specific settings
AppName=$APP_NAME
AppVersion=$APP_VERSION
InstallDirectory=$INSTALL_DIR

[Python]
# Python configuration
PythonVersion=$PYTHON_VERSION
RequirementsFile=$REQUIREMENTS_FILE

[Logging]
# Logging configuration
LogLevel=INFO
LogFile=$INSTALL_DIR\app.log

# ============================================================================
# CUSTOMIZATION NOTES:
# ============================================================================
# 
# TO CUSTOMIZE YOUR APPLICATION:
# 1. Modify the URLs above if you change default ports
# 2. Add your own configuration sections as needed
# 3. Update your Python script to read from this config file
# 4. You can use Python's configparser module to read this file
#
# EXAMPLE PYTHON CODE TO READ THIS CONFIG:
# import configparser
# config = configparser.ConfigParser()
# config.read('config.ini')
# searxng_url = config['Services']['SearXNG_URL']
# lmstudio_url = config['Services']['LMStudio_API_URL']
# ============================================================================
"@
    
    try {
        $configPath = "$INSTALL_DIR\config.ini"
        $configContent | Out-File -FilePath $configPath -Encoding UTF8
        Write-Log "Configuration file created: $configPath" -Color $Colors.Success
        return $true
    } catch {
        Write-Log "Failed to create configuration file: $($_.Exception.Message)" -Level "WARNING" -Color $Colors.Warning
        return $false
    }
}

# ==============================================================================
# MAIN INSTALLATION FUNCTION
# ==============================================================================

function Start-Installation {
    Write-Header "STARTING $APP_NAME INSTALLATION"
    
    Write-Log "Installation started with the following parameters:" -Color $Colors.Info
    Write-Log "- Skip WSL2: $SkipWSL" -Color $Colors.Info
    Write-Log "- Skip Docker: $SkipDocker" -Color $Colors.Info  
    Write-Log "- Skip LM Studio: $SkipLMStudio" -Color $Colors.Info
    Write-Log "- Skip Python: $SkipPython" -Color $Colors.Info
    Write-Log "- Force reinstall: $Force" -Color $Colors.Info
    Write-Log "- Verbose logging: $Verbose" -Color $Colors.Info
    Write-Log "- Log file: $LogPath" -Color $Colors.Info
    
    $totalSteps = 8
    $currentStep = 0
    $installationSuccessful = $true
    
    try {
        # Step 1: System requirements check
        $currentStep++
        Write-Progress-Step "Checking system requirements" $currentStep $totalSteps
        
        if (-not (Test-SystemRequirements)) {
            throw "System requirements check failed"
        }
        
        # Step 2: Create temporary directory
        $currentStep++
        Write-Progress-Step "Creating temporary directories" $currentStep $totalSteps
        Create-TempDirectory
        
        # Step 3: WSL2 Installation
        if (-not $SkipWSL) {
            $currentStep++
            Write-Progress-Step "Installing WSL2 with Debian" $currentStep $totalSteps
            
            if ($Force -or -not (Test-WSLInstalled)) {
                if (-not (Install-WSL)) {
                    Write-Log "WSL2 installation failed or requires restart" -Level "WARNING" -Color $Colors.Warning
                    $installationSuccessful = $false
                }
            } else {
                Write-Log "WSL2 with Debian is already installed (use -Force to reinstall)" -Color $Colors.Success
            }
        } else {
            $currentStep++
            Write-Progress-Step "Skipping WSL2 installation" $currentStep $totalSteps
            Write-Log "WSL2 installation skipped by user request" -Color $Colors.Info
        }
        
        # Step 4: Docker CE Installation
        if (-not $SkipDocker -and $installationSuccessful) {
            $currentStep++
            Write-Progress-Step "Installing Docker CE in WSL2" $currentStep $totalSteps
            
            if ($Force -or -not (Test-DockerInstalled)) {
                if (-not (Install-Docker)) {
                    Write-Log "Docker installation failed" -Level "WARNING" -Color $Colors.Warning
                    $installationSuccessful = $false
                }
            } else {
                Write-Log "Docker CE is already installed (use -Force to reinstall)" -Color $Colors.Success
            }
        } else {
            $currentStep++
            Write-Progress-Step "Skipping Docker installation" $currentStep $totalSteps
            if ($SkipDocker) {
                Write-Log "Docker installation skipped by user request" -Color $Colors.Info
            }
        }
        
        # Step 5: SearXNG Installation
        if ($installationSuccessful) {
            $currentStep++
            Write-Progress-Step "Setting up SearXNG search engine" $currentStep $totalSteps
            
            if ($Force -or -not (Test-SearXNGInstalled)) {
                if (-not (Install-SearXNG)) {
                    Write-Log "SearXNG installation failed" -Level "WARNING" -Color $Colors.Warning
                    $installationSuccessful = $false
                }
            } else {
                Write-Log "SearXNG is already running (use -Force to reinstall)" -Color $Colors.Success
            }
        } else {
            $currentStep++
            Write-Progress-Step "Skipping SearXNG (dependencies failed)" $currentStep $totalSteps
        }
        
        # Step 6: LM Studio Installation
        if (-not $SkipLMStudio) {
            $currentStep++
            Write-Progress-Step "Installing LM Studio" $currentStep $totalSteps
            
            if ($Force -or -not (Test-LMStudioInstalled)) {
                if (-not (Install-LMStudio)) {
                    Write-Log "LM Studio installation failed" -Level "WARNING" -Color $Colors.Warning
                    # Don't mark as failed - LM Studio is optional
                }
            } else {
                Write-Log "LM Studio is already installed (use -Force to reinstall)" -Color $Colors.Success
            }
        } else {
            $currentStep++
            Write-Progress-Step "Skipping LM Studio installation" $currentStep $totalSteps
            Write-Log "LM Studio installation skipped by user request" -Color $Colors.Info
        }
        
        # Step 7: Python Installation
        if (-not $SkipPython) {
            $currentStep++
            Write-Progress-Step "Installing Python and packages" $currentStep $totalSteps
            
            if ($Force -or -not (Test-PythonInstalled)) {
                if (Install-Python) {
                    # Install Python packages
                    if (-not (Install-PythonPackages)) {
                        Write-Log "Python package installation failed" -Level "WARNING" -Color $Colors.Warning
                        # Don't mark as failed - core Python is installed
                    }
                } else {
                    Write-Log "Python installation failed" -Level "WARNING" -Color $Colors.Warning
                    # Don't mark as failed - user might have Python elsewhere
                }
            } else {
                Write-Log "Python 3.10 is already installed (use -Force to reinstall)" -Color $Colors.Success
                # Still try to install packages
                Install-PythonPackages
            }
        } else {
            $currentStep++
            Write-Progress-Step "Skipping Python installation" $currentStep $totalSteps
            Write-Log "Python installation skipped by user request" -Color $Colors.Info
        }
        
        # Step 8: Create launcher scripts and shortcuts
        $currentStep++
        Write-Progress-Step "Creating launcher scripts and shortcuts" $currentStep $totalSteps
        
        if (-not (Create-LauncherScripts)) {
            Write-Log "Failed to create launcher scripts" -Level "WARNING" -Color $Colors.Warning
            # Don't mark as failed - installation can still work
        }
        
        # Clear progress bar
        Write-Progress -Activity "Installing $APP_NAME" -Completed
        
        # Installation summary
        Show-InstallationSummary -Success $installationSuccessful
        
    } catch {
        Write-Log "Installation failed with error: $($_.Exception.Message)" -Level "ERROR" -Color $Colors.Error
        Write-Progress -Activity "Installing $APP_NAME" -Completed
        Show-InstallationSummary -Success $false
        return $false
    } finally {
        # Cleanup temporary files
        if (Test-Path $TEMP_DIR) {
            try {
                Remove-Item $TEMP_DIR -Recurse -Force -ErrorAction SilentlyContinue
                Write-Log "Temporary files cleaned up" -Color $Colors.Info
            } catch {
                Write-Log "Could not clean up temporary files: $TEMP_DIR" -Level "WARNING" -Color $Colors.Warning
            }
        }
    }
    
    return $installationSuccessful
}

function Show-InstallationSummary {
    param([bool]$Success)
    
    Write-Host ""
    Write-Header "INSTALLATION SUMMARY"
    
    if ($Success) {
        Write-Host "🎉 INSTALLATION COMPLETED SUCCESSFULLY! 🎉" -ForegroundColor $Colors.Success
        Write-Host ""
        Write-Host "Your $APP_NAME environment is now ready to use." -ForegroundColor $Colors.Success
        Write-Host ""
        Write-Host "WHAT'S INSTALLED:" -ForegroundColor $Colors.Info
        Write-Host "✓ WSL2 with Debian Linux distribution" -ForegroundColor $Colors.Success
        Write-Host "✓ Docker CE (lightweight container engine)" -ForegroundColor $Colors.Success  
        Write-Host "✓ SearXNG search engine (http://localhost:$SEARXNG_PORT)" -ForegroundColor $Colors.Success
        Write-Host "✓ LM Studio GUI for language model management" -ForegroundColor $Colors.Success
        Write-Host "✓ Python 3.10 with required packages" -ForegroundColor $Colors.Success
        Write-Host "✓ Easy-to-use launcher scripts and desktop shortcuts" -ForegroundColor $Colors.Success
        Write-Host ""
        Write-Host "NEXT STEPS:" -ForegroundColor $Colors.Header
        Write-Host "1. 📱 Use the desktop shortcut 'Start $APP_NAME' to launch everything" -ForegroundColor White
        Write-Host "2. 🤖 Open LM Studio and download your preferred language models" -ForegroundColor White
        Write-Host "3. 📝 Place your Python application script in: $INSTALL_DIR" -ForegroundColor White
        Write-Host "4. 🚀 Run the launcher again to start your application" -ForegroundColor White
        Write-Host ""
        Write-Host "USEFUL LINKS:" -ForegroundColor $Colors.Info
        Write-Host "• SearXNG Search: http://localhost:$SEARXNG_PORT" -ForegroundColor Cyan
        Write-Host "• LM Studio API: http://localhost:$LM_STUDIO_PORT (when model loaded)" -ForegroundColor Cyan
        Write-Host "• Installation Directory: $INSTALL_DIR" -ForegroundColor Cyan
        Write-Host "• Configuration File: $INSTALL_DIR\config.ini" -ForegroundColor Cyan
        Write-Host "• Log File: $LogPath" -ForegroundColor Cyan
        
    } else {
        Write-Host "❌ INSTALLATION ENCOUNTERED ISSUES ❌" -ForegroundColor $Colors.Error
        Write-Host ""
        Write-Host "Some components may not have installed correctly." -ForegroundColor $Colors.Warning
        Write-Host "Please check the details above and the log file for more information." -ForegroundColor $Colors.Warning
        Write-Host ""
        Write-Host "TROUBLESHOOTING:" -ForegroundColor $Colors.Header
        Write-Host "• Check the installation log: $LogPath" -ForegroundColor White
        Write-Host "• Try running the installer again with -Force parameter" -ForegroundColor White
        Write-Host "• Run individual components with skip flags (e.g., -SkipWSL)" -ForegroundColor White
        Write-Host "• Ensure you have Administrator privileges" -ForegroundColor White
        Write-Host "• Check Windows version compatibility (Windows 10 2004+ or Windows 11)" -ForegroundColor White
        Write-Host ""
        Write-Host "SUPPORT:" -ForegroundColor $Colors.Info
        Write-Host "If problems persist, please:" -ForegroundColor White
        Write-Host "1. Include the log file ($LogPath) when seeking help" -ForegroundColor White
        Write-Host "2. Note your Windows version and any error messages" -ForegroundColor White
        Write-Host "3. Try manual installation of individual components" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "============================================================================" -ForegroundColor White
    Write-Host ""
}

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

# Script entry point
try {
    # Clear the screen for a clean start
    Clear-Host
    
    # Show script header
    Write-Host "============================================================================" -ForegroundColor White
    Write-Host "$APP_NAME INSTALLER v$APP_VERSION" -ForegroundColor White
    Write-Host "============================================================================" -ForegroundColor White
    Write-Host ""
    Write-Host "$APP_DESCRIPTION" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "This installer will set up everything needed to run your application:" -ForegroundColor White
    Write-Host "• WSL2 with Debian (lightweight Linux environment)" -ForegroundColor Gray
    Write-Host "• Docker CE (container engine for SearXNG)" -ForegroundColor Gray
    Write-Host "• SearXNG (privacy-focused search engine)" -ForegroundColor Gray
    Write-Host "• LM Studio (local language model interface)" -ForegroundColor Gray
    Write-Host "• Python 3.10 with required packages" -ForegroundColor Gray
    Write-Host ""
    
    # Initialize logging
    Write-Log "============================================================================" -Color $Colors.Header
    Write-Log "$APP_NAME INSTALLER v$APP_VERSION STARTED" -Color $Colors.Header
    Write-Log "============================================================================" -Color $Colors.Header
    Write-Log "Installation started by: $env:USERNAME" -Color $Colors.Info
    Write-Log "System: $env:COMPUTERNAME" -Color $Colors.Info
    Write-Log "PowerShell version: $($PSVersionTable.PSVersion)" -Color $Colors.Info
    Write-Log "Script path: $PSCommandPath" -Color $Colors.Info
    
    # Check for Administrator privileges and elevate if needed
    Request-AdminPrivileges
    
    # Wait for user confirmation unless running automated
    if (-not $Force) {
        Write-Host "IMPORTANT NOTES:" -ForegroundColor Yellow
        Write-Host "• This installation may require a system restart" -ForegroundColor Yellow
        Write-Host "• The process may take 10-30 minutes depending on your internet speed" -ForegroundColor Yellow
        Write-Host "• Administrator privileges are required" -ForegroundColor Yellow
        Write-Host "• Make sure you have at least 4GB of free disk space" -ForegroundColor Yellow
        Write-Host ""
        
        $confirmation = Read-Host "Do you want to continue with the installation? (Y/N)"
        if ($confirmation -notmatch '^[Yy]) {
            Write-Log "Installation cancelled by user" -Color $Colors.Warning
            Write-Host "Installation cancelled." -ForegroundColor Yellow
            exit 0
        }
    }
    
    Write-Host ""
    Write-Host "Starting installation..." -ForegroundColor Green
    Write-Host ""
    
    # Start the installation process
    $installationResult = Start-Installation
    
    # Final message
    if ($installationResult) {
        Write-Log "Installation completed successfully" -Color $Colors.Success
        exit 0
    } else {
        Write-Log "Installation completed with warnings or errors" -Level "WARNING" -Color $Colors.Warning
        exit 1
    }
    
} catch {
    Write-Log "Installer crashed with error: $($_.Exception.Message)" -Level "ERROR" -Color $Colors.Error
    Write-Log "Stack trace: $($_.ScriptStackTrace)" -Level "ERROR" -Color $Colors.Error
    
    Write-Host ""
    Write-Host "INSTALLER ERROR" -ForegroundColor Red
    Write-Host "The installer encountered an unexpected error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Please check the log file for details: $LogPath" -ForegroundColor Yellow
    Write-Host ""
    
    Read-Host "Press Enter to exit"
    exit 1
} finally {
    Write-Log "Installer session ended" -Color $Colors.Info
}

# ==============================================================================
# END OF INSTALLER SCRIPT
# ==============================================================================
#
# CUSTOMIZATION GUIDE FOR DEVELOPERS:
# ==============================================================================
# 
# TO ADAPT THIS SCRIPT FOR YOUR APPLICATION:
# 
# 1. UPDATE CONFIGURATION SECTION (lines 45-85):
#    - Change $APP_NAME to your application name
#    - Update $APP_DESCRIPTION with your app description  
#    - Update $REQUIREMENTS_FILE path to your requirements.txt
#    - Modify download URLs when new versions are released
# 
# 2. CUSTOMIZE LAUNCHER SCRIPTS (lines 800-1100):
#    - Update the launcher to call your specific Python script
#    - Modify service URLs and ports if different
#    - Add any additional startup checks your app needs
# 
# 3. MODIFY SYSTEM REQUIREMENTS (lines 200-300):
#    - Add checks for any additional system requirements
#    - Update minimum disk space if needed
#    - Add checks for specific hardware (GPU, etc.) if required
# 
# 4. CUSTOMIZE INSTALLATION STEPS:
#    - Add new installation functions for additional components
#    - Modify the main installation flow in Start-Installation()
#    - Update progress step counts when adding new steps
# 
# 5. UPDATE USER INSTRUCTIONS:
#    - Modify the header comments (lines 1-30) with your specific instructions
#    - Update troubleshooting information for your app
#    - Add your support contact information
# 
# 6. TESTING YOUR CUSTOMIZED INSTALLER:
#    - Test on clean Windows 10/11 virtual machines
#    - Test with different user privilege levels
#    - Test skip parameters and force reinstalls
#    - Test recovery from partial installations
# 
# 7. DISTRIBUTION:
#    - Consider code-signing the PowerShell script for trust
#    - Create a simple batch file wrapper if needed
#    - Include a README with system requirements
#    - Bundle any additional files your app needs
# 
# ==============================================================================