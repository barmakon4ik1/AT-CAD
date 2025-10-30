; Файл: lisp_helpers/get_entity.lsp
; Назначение:
;   Выбор одного объекта на чертеже.
;   Возвращает handle объекта в JSON.
;
; -----------------------
; Sprache: Deutsch
; -----------------------

(defun c:PY_GET_ENTITY ( / ent resFile f ename)
  (setq resFile (strcat (getvar "ROAMABLEROOTPREFIX") "Support\\AT-CAD\\lisp_bridge\\response.json"))
  (princ "\n[ATC] Objekt auswahlen...")

  (setq ent (entsel "\nWahlen Sie ein Objekt: "))

  (if ent
    (progn
      (setq ename (car ent))
      (setq f (open resFile "w"))
      (write-line
        (strcat "{\"handle\": \"" (cdr (assoc 5 (entget ename))) "\"}")
        f)
      (close f)
      (princ "\n[ATC] Objekt gespeichert.")
    )
    (princ "\n[ATC] Keine Auswahl getroffen.")
  )
  (princ)
)
