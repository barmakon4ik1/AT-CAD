; Файл: lisp_helpers/get_point.lsp
; Назначение:
;   Запрос точки от пользователя.
;   Возвращает координаты в response.json для Python.
;
; -----------------------
; Sprache: Deutsch
; -----------------------

(defun c:PY_GET_POINT ( / pnt resFile f)
  (setq resFile (strcat (getvar "ROAMABLEROOTPREFIX") "Support\\AT-CAD\\lisp_bridge\\response.json"))
  (princ "\n[ATC] Punktauswahl mit der Maus...")

  (setq pnt (getpoint "\nWahlen Sie einen Punkt: "))

  (if pnt
    (progn
      (setq f (open resFile "w"))
      (write-line
        (strcat "{\"x\": " (rtos (car pnt) 2 4) ", "
                "\"y\": " (rtos (cadr pnt) 2 4) ", "
                "\"z\": " (rtos (caddr pnt) 2 4) "}")
        f)
      (close f)
      (princ "\n[ATC] Punkt gespeichert.")
    )
    (princ "\n[ATC] Keine Auswahl getroffen.")
  )
  (princ)
)
