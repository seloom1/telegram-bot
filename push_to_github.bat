@echo off
chcp 65001 >nul
title رفع كود البوت إلى GitHub

echo ========================================================
echo  رفع مستودع البوت إلى حسابك في GitHub
echo ========================================================
echo.
echo 1. تأكد من إنشاء مستودع جديد (New Repository) في موقع github.com
echo 2. انسخ رابط المستودع (مثال: https://github.com/username/my-bot.git)
echo.
set /p repo_url="الصق رابط مستودع GitHub هنا: "

if "%repo_url%"=="" (
    echo [!] لم يتم إدخال رابط. تم الإلغاء.
    pause
    exit /b
)

git remote remove origin >nul 2>&1
git remote add origin %repo_url%
git branch -M main
echo [*] جاري الرفع إلى GitHub...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo  [+] تم رفع الكود بنجاح إلى GitHub!
    echo  الآن يمكنك ربطه بمنصة Render أو Koyeb لتشغيله 24/7.
    echo ========================================================
) else (
    echo.
    echo [!] حدث خطأ أثناء الرفع. تأكد من تسجيل الدخول إلى GitHub أو صحة الرابط.
)

pause
