/**
 * Translation Script for InkyPi
 * Handles translating UI elements to Traditional Chinese (zh-TW)
 * and adding a language switcher button in the header.
 */

(function initTranslation() {
    const LANG_KEY = 'inkypi-lang';
    const EN_LANG = 'en';
    const ZH_LANG = 'zh-TW';

    const TRANSLATIONS = {
        // General UI
        "Plugins": "插件",
        "Sort": "排序",
        "List": "列表",
        "Grid": "網格",
        "Drag plugins to reorder. Click \"Save\" when done.": "拖曳插件以重新排序。完成後點擊「儲存」。",
        "Save": "儲存",
        "API Keys": "API 金鑰",
        "Settings": "設定",
        "Playlists": "播放清單",
        "Toggle Dark Mode": "切換深色模式",
        "Toggle Light Mode": "切換淺色模式",
        "Back": "返回",
        "← Back": "← 返回",
        "New Playlist": "新增播放清單",
        "Displayed Now": "目前顯示",
        "Refreshed": "已重新整理",
        "Edit Refresh Settings": "編輯重新整理設定",
        "Display Now": "立即顯示",
        "Delete Plugin Instance": "刪除插件執行個體",
        "Update Playlist": "更新播放清單",
        "Playlist Name:": "播放清單名稱：",
        "Playlist Name": "播放清單名稱",
        "Display from": "顯示時間",
        "Delete": "刪除",
        "Refresh Settings": "重新整理設定",
        "Click to view full size": "點擊查看原圖",
        "Plugin:": "插件：",
        "Instance:": "執行個體：",
        "Plugin Instance Preview": "插件執行個體預覽",
        "An error occurred while processing your request.": "處理您的請求時發生錯誤。",
        "Success!": "成功！",
        "Error!": "錯誤！",
        "Save As...": "另存新檔...",
        "Add to Playlist": "新增至播放清單",
        "Playlist:": "播放清單：",
        "Instance Name:": "執行個體名稱：",
        "Requires API Key": "需要 API 金鑰",
        "Style": "樣式",
        "Frame:": "邊框：",
        "Margins:": "邊界：",
        "Top": "上",
        "Bottom": "下",
        "Left": "左",
        "Right": "右",
        "Background:": "背景：",
        "Color": "顏色",
        "Image": "圖片",
        "Upload Image": "上傳圖片",
        "Text Color:": "文字顏色：",
        "Update Now": "立即更新",
        "Refresh": "重新整理",
        "Determines how often the data and image should be refreshed.": "決定數據和圖片的重新整理頻率。",
        "Daily at": "每天固定於",
        "Every": "每",
        "Minute": "分鐘",
        "Hour": "小時",
        "Day": "日",
        "minute": "分鐘",
        "hour": "小時",
        "day": "日",

        // Settings Page
        "Download Logs": "下載日誌",
        "Reboot": "重新啟動",
        "Shutdown": "關機",
        "Device Name:": "裝置名稱：",
        "Type something...": "請輸入...",
        "Orientation:": "顯示方向：",
        "Horizontal": "橫向",
        "Vertical": "縱向",
        "Invert Image": "反轉圖片",
        "Time Zone:": "時區：",
        "Type to search...": "輸入以搜尋...",
        "Time Format:": "時間格式：",
        "12 Hour (AM/PM)": "12 小時制 (AM/PM)",
        "24 Hour": "24 小時制",
        "Plugin Cycle Interval:": "插件輪播間隔：",
        "Log System Stats": "記錄系統統計資訊",
        "Image Settings": "圖片設定",
        "Saturation:": "飽和度：",
        "Contrast:": "對比度：",
        "Sharpness:": "清晰度：",
        "Brightness:": "亮度：",
        "Inky Driver Saturation:": "Inky 驅動飽和度：",
        "The system is rebooting. The UI will be unavailable until the reboot is complete.": "系統正在重新啟動。在重啟完成前，使用者介面將無法使用。",
        "The system is shutting down. The UI will remain unavailable until it is manually restarted.": "系統正在關機。在手動重新啟動前，使用者介面將保持無法使用狀態。",
        "Success! Settings saved.": "成功！設定已儲存。",
        "Success! Settings saved": "成功！設定已儲存",

        // API Keys Page
        "No API keys configured yet.": "尚未設定任何 API 金鑰。",
        "Add keys below to enable plugin features.": "在下方新增金鑰以啟用插件功能。",
        "+ Add API Key": "+ 新增 API 金鑰",
        "API keys are stored in the .env file on the device.": "API 金鑰儲存在裝置的 .env 檔案中。",
        "For security, existing values are never displayed. To change a key, delete it and add a new one.": "為安全起見，不顯示現有的值。如需變更，請刪除並新增一個。",
        "Some plugins may require a restart after changing keys.": "變更金鑰後，部分插件可能需要重新啟動。",
        "Please enter a value for new API keys": "請為新的 API 金鑰輸入值",
        "Failed to save API keys": "儲存 API 金鑰失敗",
        "KEY_NAME": "金鑰名稱",
        "Enter value": "輸入金鑰值",

        // Common Plugin Config Labels
        "Location: ": "地點：",
        "Location": "地點",
        "Latitude ": "緯度 ",
        "Longitude ": "經度 ",
        "Select Location": "選擇位置",
        "Weather Provider:": "天氣供應商：",
        "Units:": "單位：",
        "Metric (°C)": "公制 (°C)",
        "Imperial (°F)": "英制 (°F)",
        "Standard (K)": "標準 (K)",
        "Title:": "標題：",
        "Custom": "自訂",
        "Display: ": "顯示：",
        "Refresh Time": "更新時間",
        "Metrics": "指標",

        // Validation Errors
        "Please select a refresh type": "請選擇重新整理類型",
        "Please enter a valid interval": "請輸入有效的間隔時間",
        "Please select a time unit": "請選擇時間單位",
        "Please select a refresh time": "請選擇重新整理時間",

        // Other buttons & items
        "Choose file": "選擇檔案",
        "No file chosen": "未選擇檔案",
        "Search": "搜尋",
        "Save Plugin Order": "儲存插件順序"
    };

    /**
     * Translates a relative time string.
     */
    function translateRelativeTime(text) {
        text = text.trim();
        if (text === "just now") return "剛剛";
        if (text.endsWith(" minutes ago")) {
            const mins = text.replace(" minutes ago", "");
            return mins + " 分鐘前";
        }
        if (text.endsWith(" hours ago")) {
            const hrs = text.replace(" hours ago", "");
            return hrs + " 小時前";
        }
        if (text.startsWith("today at ")) {
            return text.replace("today at ", "今天 ");
        }
        if (text.startsWith("yesterday at ")) {
            return text.replace("yesterday at ", "昨天 ");
        }

        const months = {
            "Jan": "1月", "Feb": "2月", "Mar": "3月", "Apr": "4月", "May": "5月", "Jun": "6月",
            "Jul": "7月", "Aug": "8月", "Sep": "9月", "Oct": "10月", "Nov": "11月", "Dec": "12月"
        };
        for (const [en, zh] of Object.entries(months)) {
            if (text.startsWith(en + " ")) {
                let replaced = text.replace(new RegExp(en + "\\s+(\\d+)\\s+at\\s+", "i"), `${zh}$1日 `);
                return replaced;
            }
        }
        return text;
    }

    /**
     * Translate the DOM elements recursively.
     */
    function translateDOM(root) {
        if (!root) root = document.body;

        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
        let textNode;
        while (textNode = walker.nextNode()) {
            const parent = textNode.parentNode;
            if (parent && (parent.tagName === 'SCRIPT' || parent.tagName === 'STYLE' || parent.tagName === 'TEXTAREA')) {
                continue;
            }
            const text = textNode.nodeValue;
            const trimmed = text.trim();

            if (TRANSLATIONS[trimmed]) {
                const leading = text.match(/^\s*/)[0];
                const trailing = text.match(/\s*$/)[0];
                textNode.nodeValue = leading + TRANSLATIONS[trimmed] + trailing;
            } else if (trimmed.startsWith("Refreshed ")) {
                const timeStr = trimmed.substring(10);
                const translatedTime = translateRelativeTime(timeStr);
                const leading = text.match(/^\s*/)[0];
                const trailing = text.match(/\s*$/)[0];
                textNode.nodeValue = leading + "已於 " + translatedTime + " 重新整理" + trailing;
            }
        }

        const elements = root.querySelectorAll('[placeholder], [title], [alt], input[type="button"], input[type="submit"]');
        elements.forEach(el => {
            if (el.hasAttribute('placeholder')) {
                const val = el.getAttribute('placeholder').trim();
                if (TRANSLATIONS[val]) {
                    el.setAttribute('placeholder', TRANSLATIONS[val]);
                }
            }
            if (el.hasAttribute('title')) {
                const val = el.getAttribute('title').trim();
                if (TRANSLATIONS[val]) {
                    el.setAttribute('title', TRANSLATIONS[val]);
                }
            }
            if (el.hasAttribute('alt')) {
                const val = el.getAttribute('alt').trim();
                if (TRANSLATIONS[val]) {
                    el.setAttribute('alt', TRANSLATIONS[val]);
                }
            }
            if (el.tagName === 'INPUT' && (el.type === 'button' || el.type === 'submit')) {
                const val = el.value.trim();
                if (TRANSLATIONS[val]) {
                    el.value = TRANSLATIONS[val];
                }
            }
        });
    }

    /**
     * Inserts the language switcher button into the page.
     */
    function addLanguageToggle() {
        // Avoid duplicate toggles
        if (document.querySelector('.lang-toggle')) return;

        const isMainPage = document.querySelector('.dark-mode-toggle') !== null;
        const currentLang = localStorage.getItem(LANG_KEY) || EN_LANG;

        const langBtn = document.createElement('button');
        langBtn.className = 'settings-button lang-toggle';
        langBtn.title = 'Switch Language / 切換語言';
        langBtn.setAttribute('aria-label', 'Switch Language');
        langBtn.style.fontSize = '1rem';
        langBtn.style.cursor = 'pointer';
        langBtn.style.display = 'inline-flex';
        langBtn.style.alignItems = 'center';
        langBtn.style.justifyContent = 'center';
        langBtn.style.gap = '5px';

        if (currentLang === ZH_LANG) {
            langBtn.innerHTML = '<span style="font-size: 1.1rem;">🌐</span> EN';
        } else {
            langBtn.innerHTML = '<span style="font-size: 1.1rem;">🌐</span> 繁';
        }

        langBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const nextLang = currentLang === EN_LANG ? ZH_LANG : EN_LANG;
            localStorage.setItem(LANG_KEY, nextLang);
            window.location.reload();
        });

        if (isMainPage) {
            // Main page: insert next to dark mode toggle
            const darkToggle = document.querySelector('.dark-mode-toggle');
            if (darkToggle) {
                darkToggle.parentNode.insertBefore(langBtn, darkToggle.nextSibling);
            } else {
                const header = document.querySelector('.header');
                if (header) header.appendChild(langBtn);
            }
        } else {
            // Other pages
            const headerContent = document.querySelector('.header-content');
            if (headerContent) {
                const children = Array.from(headerContent.children);
                if (children.length > 1) {
                    // There is an actions div (e.g. settings page)
                    children[1].insertBefore(langBtn, children[1].firstChild);

                    langBtn.style.backgroundColor = 'var(--bg-secondary, #eee)';
                    langBtn.style.color = 'var(--text-primary, #333)';
                    langBtn.style.padding = '8px 12px';
                    langBtn.style.borderRadius = '8px';
                    langBtn.style.border = 'none';
                    langBtn.style.marginRight = '8px';
                } else {
                    // Only title exists, append container and button
                    const btnContainer = document.createElement('div');
                    btnContainer.appendChild(langBtn);
                    headerContent.appendChild(btnContainer);

                    langBtn.style.backgroundColor = 'var(--bg-secondary, #eee)';
                    langBtn.style.color = 'var(--text-primary, #333)';
                    langBtn.style.padding = '8px 12px';
                    langBtn.style.borderRadius = '8px';
                    langBtn.style.border = 'none';
                }
            } else {
                // Fallback to top left of frame
                const frame = document.querySelector('.frame');
                if (frame) {
                    const topBar = document.createElement('div');
                    topBar.style.display = 'flex';
                    topBar.style.justifyContent = 'flex-end';
                    topBar.style.width = '100%';
                    topBar.appendChild(langBtn);
                    frame.insertBefore(topBar, frame.firstChild);
                }
            }
        }
    }

    /**
     * Intercept showResponseModal to translate dynamic modal messages
     */
    function interceptResponseModal() {
        const originalShowResponseModal = window.showResponseModal;
        if (typeof originalShowResponseModal === 'function') {
            window.showResponseModal = function(status, message) {
                let translatedMsg = message;
                const trimmedMsg = message.trim();
                
                // Try translation of the whole message
                if (TRANSLATIONS[trimmedMsg]) {
                    translatedMsg = TRANSLATIONS[trimmedMsg];
                } else {
                    // Check standard success/failure strings with variable content
                    // e.g. "Success! Settings saved" -> "成功！設定已儲存"
                    // e.g. "Success! Deleted playlist 'xyz'!" -> "成功！已刪除播放清單 'xyz'！"
                    if (trimmedMsg.startsWith("Success! ")) {
                        let inner = trimmedMsg.substring(9);
                        if (inner.startsWith("Deleted playlist '") && inner.endsWith("'!")) {
                            const name = inner.substring(18, inner.length - 2);
                            translatedMsg = `成功！已刪除播放清單 '${name}'！`;
                        } else if (TRANSLATIONS[inner.trim()]) {
                            translatedMsg = `成功！${TRANSLATIONS[inner.trim()]}`;
                        }
                    }
                }
                originalShowResponseModal(status, translatedMsg);
            };
        }
    }

    function initialize() {
        // Always add the button first
        addLanguageToggle();

        const currentLang = localStorage.getItem(LANG_KEY) || EN_LANG;
        if (currentLang === ZH_LANG) {
            // Apply translation to initial DOM
            translateDOM();

            // Set up MutationObserver to translate future changes
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1) { // ELEMENT_NODE
                            translateDOM(node);
                        }
                    });
                });
            });
            observer.observe(document.body, { childList: true, subtree: true });

            // Intercept modal calls
            interceptResponseModal();
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
})();
