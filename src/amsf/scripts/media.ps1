$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$managerType=[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime]
$mediaType=[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties,Windows.Media.Control,ContentType=WindowsRuntime]
$asTask=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {$_.Name -eq 'AsTask' -and $_.IsGenericMethodDefinition -and $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'} | Select-Object -First 1
function AwaitOperation($operation,[Type]$type){
    $task=$asTask.MakeGenericMethod($type).Invoke($null,@($operation))
    if(!$task.Wait(6000)){throw 'Media request timed out'}
    $task.Result
}
$manager=AwaitOperation ($managerType::RequestAsync()) $managerType
foreach($session in $manager.GetSessions()){
    if($session.SourceAppUserModelId -notmatch '^AppleInc\.AppleMusicWin_'){continue}
    $media=AwaitOperation ($session.TryGetMediaPropertiesAsync()) $mediaType
    $timeline=$session.GetTimelineProperties()
    [pscustomobject]@{Title=$media.Title;Artist=$media.Artist;Status=$session.GetPlaybackInfo().PlaybackStatus.ToString();Position=$timeline.Position.TotalSeconds;Duration=$timeline.EndTime.TotalSeconds;Updated=$timeline.LastUpdatedTime.ToUniversalTime().ToString('o',[Globalization.CultureInfo]::InvariantCulture)} | ConvertTo-Json -Compress
    exit
}
'null'
