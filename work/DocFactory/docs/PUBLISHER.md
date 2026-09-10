# Издатель / предупреждение Windows («Неизвестный издатель»)

Окно при запуске `start.bat` — это **не настройка DocFactory**, а защита Windows
(SmartScreen / Zone.Identifier у файлов, скачанных из интернета или с флешки).

## Можно ли написать «Известный издатель rva» в этом окне?

| Тип файла | Можно ли своё имя издателя |
|-----------|----------------------------|
| `.bat` / `.ps1` | **Нет** — у пакетных файлов нет поля «Publisher» в этом диалоге |
| `.exe` | **Да**, если файл **подписан** сертификатом (Authenticode) |

То есть надпись «Неизвестный издатель» у `start.bat` стандартная и **не редактируется** строкой в коде.

## Что можно сделать practically

### 1. Убрать надоедливый запрос (без смены издателя)

После копирования с GitHub/флешки в PowerShell:

```powershell
Get-ChildItem -Path D:\Work\DocFactory -Recurse | Unblock-File
```

Или снимите галочку «Всегда спрашивать…» и нажмите **Запустить**.

`INSTALL.bat` теперь тоже пытается снять блокировку зоны.

### 2. Ярлык вместо открытия .bat двойным кликом

`INSTALL.bat` создаёт `DocFactory.lnk` на рабочем столе (через PowerShell) —
так реже всплывает диалог «издатель».

### 3. Настоящий издатель «rva» — только через подписанный EXE

1. Соберите `build_exe.bat` → `dist\DocFactory.exe`
2. Создайте **самоподписанный** сертификат (для себя/внутри организации):

```powershell
$cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=Izvestnyy izdatel rva" -CertStoreLocation Cert:\CurrentUser\My
Export-Certificate -Cert $cert -FilePath D:\Work\DocFactory\rva-codesign.cer
```

3. Подпишите exe (`signtool` из Windows SDK):

```text
signtool sign /fd SHA256 /a /n "Izvestnyy izdatel rva" DocFactory.exe
```

На чужих ПК Windows всё равно может писать «недоверенный издатель», пока сертификат
не добавлен в доверенные — для домашнего/служебного ПК без IT это нормально.

**Вывод:** в окно про `start.bat` вписать «rva» нельзя; для бренда издателя нужен
подписанный `.exe`. Для ежедневной работы достаточно Unblock-File + ярлык.
