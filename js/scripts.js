$(document).ready(function () {
  $("table").DataTable({
    order: [[6, "asc"]],
    paging: true,
    lengthMenu: [10, 25, 50, 100],
    language: {
      search: "Buscar:",
      lengthMenu: "Mostrar _MENU_ registros",
      info: "Mostrando _START_ a _END_ de _TOTAL_ registros",
      infoEmpty: "No hay registros disponibles",
      infoFiltered: "(filtrado de _MAX_ registros totales)",
      paginate: {
        first: "Primero",
        last: "Último",
        next: "Siguiente",
        previous: "Anterior",
      },
    },
    responsive: true,
  });

  // Aplicar filtro CASTLES al cambiar el checkbox
  $("#filter_castles").on("change", function () {
    $("form").submit();
  });
});
