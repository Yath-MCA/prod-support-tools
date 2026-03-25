import { execSync } from "child_process";

export function killChromium() {
    try {
        if (process.platform === "win32") {
            execSync('taskkill /F /IM chrome.exe /T', { stdio: 'ignore' });
            execSync('taskkill /F /IM chromium.exe /T', { stdio: 'ignore' });
        } else if (process.platform === "darwin") {
            execSync('killall Chrome', { stdio: 'ignore' });
            execSync('killall Chromium', { stdio: 'ignore' });
        } else {
            execSync('pkill chrome', { stdio: 'ignore' });
            execSync('pkill chromium', { stdio: 'ignore' });
        }
    } catch (err) {
        // ignore errors if browser was not open
    }
}
