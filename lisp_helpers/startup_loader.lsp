; Файл: lisp_helpers/startup_loader.lsp
; Назначение:
;   Автоматическая загрузка LISP-модулей проекта AT-CAD при запуске AutoCAD.
;   Работает в любой локализации (в т.ч. немецкой).
;
; -----------------------
; Важно:
;   Кодировка файла — ANSI (Windows-1251)
; -----------------------

(defun c:ATC_LOAD ( / base lispDir files f)
  (princ "\n[ATC-Init] Загрузка LISP-модулей проекта AT-CAD...")

  ;; Определяем базовую директорию (где проект установлен)
  (setq base "E:\\AT-CAD\\")
  (setq lispDir (strcat base "lisp_helpers\\"))

  ;; Список файлов для загрузки
  (setq files '("get_point.lsp" "get_entity.lsp" "bridge.lsp"))

  ;; Загружаем каждый
  (foreach f files
    (setq fullpath (strcat lispDir f))
    (if (findfile fullpath)
      (progn
        (load fullpath)
        (princ (strcat "\n[OK] ЗАГРУЖЕНО: " f))
      )
      (princ (strcat "\n[Ошибка] Не найден: " f))
    )
  )

  (princ "\n[ATC-Init] Загрузка завершена. Запустите ATC_BRIDGE_START для активации моста.")
  (princ)
)

(princ "\n[ATC-Init] Готово. Выполните команду ATC_LOAD для загрузки LISP-модулей.")
(princ)
