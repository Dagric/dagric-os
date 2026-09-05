# Dagric Windows Companion — run this while logged into the Windows account
# being moved. It inventories settings Windows alone can see; it does not
# export passwords, DPAPI secrets, Windows Hello, BitLocker keys, or cookies.
[CmdletBinding()]
param(
  [string]$OutPath = (Join-Path $env:USERPROFILE 'Desktop\Dagric-Windows-Companion.json'),
  [switch]$Encrypt
)
$ErrorActionPreference = 'SilentlyContinue'
function Names($items, $property) { @($items | ForEach-Object { $_.$property } | Where-Object { $_ } | Sort-Object -Unique) }
$apps = @()
Get-ItemProperty 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*','HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*' | ForEach-Object {
  if ($_.DisplayName) { $apps += [pscustomobject]@{ name=$_.DisplayName; version=$_.DisplayVersion; publisher=$_.Publisher } }
}
$oneDrive = Get-ChildItem (Join-Path $env:USERPROFILE 'OneDrive*') -Directory | Select-Object -ExpandProperty FullName
$data = [ordered]@{
  format='dagric-windows-companion'; version=1; created_utc=(Get-Date).ToUniversalTime().ToString('o')
  privacy='Inventory only: no passwords, cookies, DPAPI secrets, Windows Hello, BitLocker keys, or Wi-Fi passwords.'
  applications=@($apps | Sort-Object name -Unique)
  network=@{ wifi_ssids=(Names (netsh wlan show profiles | Select-String 'All User Profile') Line | ForEach-Object { ($_ -split ':',2)[1].Trim() }); adapters=@(Get-NetAdapter | Select-Object Name,InterfaceDescription,Status,MacAddress) }
  peripherals=@{ printers=@(Get-Printer | Select-Object Name,DriverName,PortName); bluetooth=(Names (Get-PnpDevice -Class Bluetooth) FriendlyName); displays=@(Get-CimInstance -Namespace root\\wmi -ClassName WmiMonitorID | ForEach-Object { [Text.Encoding]::ASCII.GetString($_.UserFriendlyName) -replace [char]0,'' }) }
  developer=@{ wsl_distributions=(Names (wsl -l -q) ToString); vscode_extensions=(Names (code --list-extensions) ToString) }
  cloud=@{ onedrive_roots=@($oneDrive); note='Cloud-only files must be made available offline before a Linux migration can copy them.' }
}
$json = $data | ConvertTo-Json -Depth 7
if (-not $Encrypt) { [IO.File]::WriteAllText($OutPath,$json,[Text.UTF8Encoding]::new($false)); Write-Host "Created $OutPath"; exit 0 }
$plain = Read-Host 'Choose a transfer passphrase' -AsSecureString
$ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($plain); try { $password=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
$salt=New-Object byte[] 16; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($salt)
$kdf=New-Object Security.Cryptography.Rfc2898DeriveBytes($password,$salt,200000,[Security.Cryptography.HashAlgorithmName]::SHA256); $key=$kdf.GetBytes(64)
$aes=[Security.Cryptography.Aes]::Create(); $aes.Key=$key[0..31]; $aes.GenerateIV(); $cipher=$aes.CreateEncryptor().TransformFinalBlock([Text.Encoding]::UTF8.GetBytes($json),0,[Text.Encoding]::UTF8.GetByteCount($json))
$mac=New-Object Security.Cryptography.HMACSHA256(,$key[32..63]); $tag=$mac.ComputeHash($salt+$aes.IV+$cipher)
$bundle=[ordered]@{format='dagric-windows-companion-encrypted';version=1;kdf='PBKDF2-SHA256';iterations=200000;salt=[Convert]::ToBase64String($salt);iv=[Convert]::ToBase64String($aes.IV);ciphertext=[Convert]::ToBase64String($cipher);hmac=[Convert]::ToBase64String($tag)} | ConvertTo-Json
$target=[IO.Path]::ChangeExtension($OutPath,'dagric')
[IO.File]::WriteAllText($target,$bundle,[Text.UTF8Encoding]::new($false)); Write-Host "Created encrypted $target. Keep its passphrase separate."
