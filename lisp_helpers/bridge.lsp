; Файл: lisp_helpers/bridge.lsp
; Автор: ChatGPT (адаптировано под проект AT-CAD)
;
; Назначение:
;   Главный мост AutoLISP ↔ Python.
;   Автоматически следит за JSON-запросами из Python (request.json)
;   и вызывает нужную подпрограмму (get_point / get_entity и т.д.)
;
; Принцип работы:
;   - При старте AutoCAD подгружается bridge.lsp (добавляется в автозагрузку).
;   - Фоновая функция периодически проверяет наличие request.json.
;   - При нахождении — анализирует команду ("get_point" и т.п.),
;     вызывает соответствующий c:PY_* обработчик,
;     который создаёт response.json для Python.
;   - После выполнения request.json удаляется.
;
; Работает без COM, только средствами LISP + файловый обмен.
;

(defun ATC-Bridge-Loop ( / reqFile resFile reqData command)
  (setq reqFile (findfile "programs/../lisp_bridge/request.json"))
  (setq resFile (findfile "programs/../lisp_bridge/response.json"))

  (if (and reqFile (findfile reqFile))
    (progn
      (setq f (open reqFile "r"))
      (setq reqData (read-line f))
      (close f)

      ; Определяем тип команды
      (cond
        ((vl-string-search "\"get_point\"" reqData)
          (princ "\n[ATC-Bridge] Запрошена точка Python → LISP...")
          (c:PY_GET_POINT)
        )
        ((vl-string-search "\"get_entity\"" reqData)
          (princ "\n[ATC-Bridge] Запрошен объект Python → LISP...")
          (c:PY_GET_ENTITY)
        )
        (t
          (princ "\n[ATC-Bridge] Неизвестная команда.")
        )
      )

      (vl-file-delete reqFile)
    )
  )

  ; Повторить проверку через 1 секунду
  (vlr-set-notification
    (vlr-timer-reactor nil '((nil) (ATC-Bridge-Loop)))
    1000
  )
  (princ)
)

; === Инициализация моста при загрузке ===
(defun C:ATC_BRIDGE_START ( / )
  (princ "\n[ATC-Bridge] Автоматический мост Python↔LISP запущен.")
  (ATC-Bridge-Loop)
  (princ)
)

(princ "\n[ATC-Bridge] Мост готов. Введите команду ATC_BRIDGE_START для активации.")
(princ)
