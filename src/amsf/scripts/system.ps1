param([ValidateSet('discover','close','launch','authorize','guard')][string]$Action='discover')
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
if($Action -eq 'guard'){
    $processes=@(Get-CimInstance Win32_Process -Filter "Name='AppleMusic.exe' OR Name='AMPLibraryAgent.exe' OR Name='AppleTV.exe'")
    @{closed=($processes.Count -eq 0)} | ConvertTo-Json -Compress
    exit
}
$pkg=Get-AppxPackage -Name AppleInc.AppleMusicWin | Select-Object -First 1
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
function MusicProcesses {
    if(!$pkg){return @()}
    @(Get-CimInstance Win32_Process -Filter "Name='AppleMusic.exe' OR Name='AMPLibraryAgent.exe'" | Where-Object {
        $owner=Invoke-CimMethod -InputObject $_ -MethodName GetOwnerSid
        $owner.Sid -eq $sid -and $_.ExecutablePath -and $_.ExecutablePath.StartsWith($pkg.InstallLocation+'\',[StringComparison]::OrdinalIgnoreCase)
    })
}
if($Action -eq 'discover'){
    $build=[Environment]::OSVersion.Version.Build
    [pscustomobject]@{installed=[bool]$pkg;version=if($pkg){$pkg.Version.ToString()}else{''};build=$build;
        supported=($build -ge 22000 -and [Environment]::Is64BitOperatingSystem -and $env:PROCESSOR_ARCHITECTURE -eq 'AMD64');
        sid=$sid;install=if($pkg){$pkg.InstallLocation}else{''};
        package_data=if($pkg){Join-Path $env:LOCALAPPDATA ('Packages\'+$pkg.PackageFamilyName)}else{''};
        preferences=if($pkg){Join-Path $env:LOCALAPPDATA ('Packages\'+$pkg.PackageFamilyName+'\LocalCache\Roaming\Apple Computer\Preferences')}else{''};
        running=@(MusicProcesses).Count -gt 0} | ConvertTo-Json -Compress
    exit
}
if(!$pkg){throw 'Apple Music is not installed for the current user.'}
if($Action -eq 'close'){
    foreach($p in (MusicProcesses | Where-Object Name -eq 'AppleMusic.exe')){
        $process=Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue
        if($process){$process.CloseMainWindow() | Out-Null}
    }
    for($i=0;$i -lt 20;$i++){
        if(@(MusicProcesses).Count -eq 0){ @{closed=$true} | ConvertTo-Json -Compress;exit }
        Start-Sleep -Seconds 1
    }
    @{closed=$false} | ConvertTo-Json -Compress
    exit
}
Start-Process explorer.exe ('shell:AppsFolder\'+$pkg.PackageFamilyName+'!App') -WindowStyle Hidden
if($Action -eq 'launch'){ @{opened=$true;authorization_opened=$false} | ConvertTo-Json -Compress;exit }
# Only navigation controls are inspected. Password/edit controls are never read or written.
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
for($i=0;$i -lt 25;$i++){
    $ids=@(MusicProcesses | Where-Object Name -eq 'AppleMusic.exe' | Select-Object -ExpandProperty ProcessId)
    $root=[System.Windows.Automation.AutomationElement]::RootElement
    $window=$root.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition) | Where-Object {$_.Current.ProcessId -in $ids} | Select-Object -First 1
    if($window){break}; Start-Sleep -Milliseconds 300
}
$opened=$false
try {
    $label=$window.FindFirst([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::AutomationIdProperty,'lowerAccountName'))
    if($label){
        $parent=[System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($label)
        $parent.SetFocus()
        (New-Object -ComObject WScript.Shell).SendKeys('{ENTER}')
        Start-Sleep -Milliseconds 400
        $target=$window.FindFirst([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,'Authorize Machine'))
        if($target -and $target.Current.ControlType -eq [System.Windows.Automation.ControlType]::Hyperlink){
            $target.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke();$opened=$true
        }
    }
} catch { $opened=$false }
@{opened=$true;authorization_opened=$opened} | ConvertTo-Json -Compress
