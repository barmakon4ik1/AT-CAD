; Файл: lisp_helpers/startup_loader.lsp
; Назначение:
;   Загружает все вспомогательные LISP-файлы проекта AT-CAD при запуске AutoCAD.
;
; Поддерживает:
;   - get_point.lsp
;   - get_entity.lsp
;   - bridge.lsp

(defun C:ATC_LOAD ()
  (princ "\n[ATC-Init] Загрузка LISP-модулей проекта AT-CAD...")

  (setq base (getvar "ROAMABLEROOTPREFIX"))
  (setq atcdir (strcat base "Support\\AT-CAD\\lisp_helpers\\"))

  (foreach file '("get_point.lsp" "get_entity.lsp" "bridge.lsp")
    (if (findfile (strcat atcdir file))
      (progn
        (load (strcat atcdir file))
        (princ (strcat "\n[OK] Загружен: " file))
      )
      (princ (strcat "\n[Ошибка] Не найден: " file))
    )
  )

  (princ "\n[ATC-Init] Загрузка завершена. Запустите ATC_BRIDGE_START для активации моста.")
  (princ)
)
