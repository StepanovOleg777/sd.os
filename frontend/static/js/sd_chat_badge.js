(() => {
    const badges =
        document.querySelectorAll(
            "[data-sd-chat-unread-badge]"
        );

    if (!badges.length) {
        return;
    }


    async function getJson(url) {
        const response =
            await fetch(
                url,
                {
                    credentials:
                        "same-origin",

                    cache:
                        "no-store",
                }
            );

        if (!response.ok) {
            throw new Error(
                "Не удалось получить счётчик сообщений."
            );
        }

        return await response.json();
    }


    function updateBadges(total) {
        badges.forEach(
            badge => {
                if (total > 0) {
                    badge.textContent =
                        total > 99
                            ? "99+"
                            : String(total);

                    badge.style.display =
                        "inline-flex";

                } else {
                    badge.textContent =
                        "";

                    badge.style.display =
                        "none";
                }
            }
        );
    }


    async function loadUnreadCount() {
        try {
            const [
                conversationsData,
                announcementData,
            ] = await Promise.all([
                getJson(
                    "/api/sd-chat/conversations"
                ),

                getJson(
                    "/api/sd-chat/announcement-counts"
                ),
            ]);


            const conversations =
                conversationsData.conversations
                || [];


            const messageUnread =
                conversations.reduce(
                    (
                        total,
                        conversation
                    ) => {
                        return (
                            total
                            + Number(
                                conversation
                                    .unread_count
                                || 0
                            )
                        );
                    },
                    0
                );


            const announcementUnread =
                Number(
                    announcementData.unread
                    || 0
                );


            updateBadges(
                messageUnread
                + announcementUnread
            );

        } catch (error) {
            console.error(
                "Не удалось обновить счётчик сообщений:",
                error
            );
        }
    }


    window.SDOSChatBadge = {
        refresh:
            loadUnreadCount,
    };


    /*
     * Первичная загрузка.
     */
    loadUnreadCount();


    /*
     * Обновляем при возврате на страницу.
     * Это важно, например, при кнопке "Назад",
     * когда браузер восстанавливает страницу из кэша.
     */
    window.addEventListener(
        "pageshow",
        () => {
            loadUnreadCount();
        }
    );


    /*
     * Обновляем, когда пользователь возвращается
     * во вкладку SD.OS.
     */
    window.addEventListener(
        "focus",
        () => {
            loadUnreadCount();
        }
    );


    /*
     * Обновляем после возврата из другой вкладки
     * или после сворачивания браузера.
     */
    document.addEventListener(
        "visibilitychange",
        () => {
            if (
                document.visibilityState
                === "visible"
            ) {
                loadUnreadCount();
            }
        }
    );
})();