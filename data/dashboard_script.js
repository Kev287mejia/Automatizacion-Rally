
document.addEventListener(
  "DOMContentLoaded",
  function () {
    "use strict";

    const dashboard = document.getElementById(
      "dashboardSeguimiento"
    );

    if (!dashboard) {
      return;
    }

    if (
      typeof Chart !== "undefined"
      && typeof ChartDataLabels !== "undefined"
    ) {
      Chart.register(
        ChartDataLabels
      );
    }

    const formulario = document.getElementById(
      "formFiltrosDashboard"
    );

    const filtroEdicion = document.getElementById(
      "filtroEdicion"
    );

    const filtroInstitucion = document.getElementById(
      "filtroInstitucion"
    );

    const filtroSede = document.getElementById(
      "filtroSede"
    );

    const cargando = document.getElementById(
      "dashboardCargando"
    );

    const alerta = document.getElementById(
      "dashboardAlerta"
    );

    const alertaMensaje = document.getElementById(
      "dashboardAlertaMensaje"
    );

    const estadoActualizacion = document.getElementById(
      "estadoActualizacionDashboard"
    );

    const urlDatos = dashboard.dataset.urlDatos;
    const urlSedes = dashboard.dataset.urlSedes;

    const $ = (
      typeof window.jQuery !== "undefined"
      ? window.jQuery
      : null
    );

    let solicitudDashboard = null;
    let solicitudSedes = null;

    const graficos = {
      sexos: null,
      etnias: null,
      retos: null,
      categorias: null
    };

    const tablas = {
      sedes: {
        datos: [],
        filtrados: [],
        pagina: 1,
        porPagina: 10
      },
      departamentos: {
        datos: [],
        filtrados: [],
        pagina: 1,
        porPagina: 10
      },
      municipios: {
        datos: [],
        filtrados: [],
        pagina: 1,
        porPagina: 10
      }
    };


    function numeroSeguro(valor) {
      const numero = Number(valor);

      return Number.isFinite(numero)
        ? numero
        : 0;
    }


    function escaparHtml(valor) {
      return String(valor ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }


    function inicializarSelect2Dashboard() {
      if (
        !$ ||
        typeof $.fn.select2 === "undefined"
      ) {
        return;
      }

      $(".select2-dashboard").each(
        function () {
          const selector = $(this);

          if (
            selector.hasClass(
              "select2-hidden-accessible"
            )
          ) {
            selector.select2("destroy");
          }

          selector.select2({
            theme: "bootstrap-5",
            width: "100%",
            allowClear: false,
            minimumResultsForSearch: 6,
            language: {
              noResults: function () {
                return "No se encontraron resultados";
              },
              searching: function () {
                return "Buscando...";
              }
            }
          });
        }
      );
    }


    function mostrarCarga() {
      cargando.classList.add("visible");

      cargando.setAttribute(
        "aria-hidden",
        "false"
      );

      if (estadoActualizacion) {
        estadoActualizacion.classList.add(
          "actualizando"
        );

        estadoActualizacion.innerHTML = (
          '<span class="spinner-border '
          + 'spinner-border-sm"></span>'
          + '<span>Actualizando datos...</span>'
        );
      }
    }


    function ocultarCarga() {
      cargando.classList.remove("visible");

      cargando.setAttribute(
        "aria-hidden",
        "true"
      );

      if (estadoActualizacion) {
        estadoActualizacion.classList.remove(
          "actualizando"
        );

        estadoActualizacion.innerHTML = (
          '<i class="fa-solid fa-circle-check"></i>'
          + '<span>Datos actualizados</span>'
        );
      }
    }


    function mostrarError(mensaje) {
      alertaMensaje.textContent = (
        mensaje
        || "Ocurrió un error inesperado."
      );

      alerta.classList.add("visible");
    }


    function ocultarError() {
      alerta.classList.remove("visible");
      alertaMensaje.textContent = "";
    }


    function actualizarTexto(
      id,
      valor
    ) {
      const elemento = document.getElementById(id);

      if (elemento) {
        elemento.textContent = valor;
      }
    }


    function destruirGrafico(nombre) {
      if (graficos[nombre]) {
        graficos[nombre].destroy();
        graficos[nombre] = null;
      }
    }


    function alternarSinDatos(
      canvasId,
      mensajeId,
      tieneDatos
    ) {
      const canvas = document.getElementById(
        canvasId
      );

      const mensaje = document.getElementById(
        mensajeId
      );

      canvas.parentElement.style.display = (
        tieneDatos
        ? "block"
        : "none"
      );

      mensaje.classList.toggle(
        "visible",
        !tieneDatos
      );
    }


    function obtenerParametros() {
      const parametros = new URLSearchParams();

      if (
        filtroEdicion
        && filtroEdicion.value
      ) {
        parametros.set(
          "edicion",
          filtroEdicion.value
        );
      }

      if (
        filtroInstitucion
        && filtroInstitucion.value
      ) {
        parametros.set(
          "institucion",
          filtroInstitucion.value
        );
      }

      if (
        filtroSede
        && filtroSede.value
      ) {
        parametros.set(
          "sede",
          filtroSede.value
        );
      }

      return parametros;
    }


    function actualizarIndicadores(datos) {
      const indicadores = datos.indicadores || {};

      actualizarTexto(
        "indicadorInscritos",
        numeroSeguro(
          indicadores.inscritos
        ).toLocaleString("es-NI")
      );

      actualizarTexto(
        "indicadorParticipantes",
        numeroSeguro(
          indicadores.participantes
        ).toLocaleString("es-NI")
      );

      actualizarTexto(
        "indicadorMentores",
        numeroSeguro(
          indicadores.mentores
        ).toLocaleString("es-NI")
      );

      actualizarTexto(
        "indicadorCoordinadoresSede",
        numeroSeguro(
          indicadores.coordinadores_sede
        ).toLocaleString("es-NI")
      );

      actualizarTexto(
        "indicadorJurados",
        numeroSeguro(
          indicadores.jurados
        ).toLocaleString("es-NI")
      );

      actualizarTexto(
        "indicadorJuradosNacionales",
        numeroSeguro(
          indicadores.jurados_nacionales
        ).toLocaleString("es-NI")
      );

      actualizarTexto(
        "indicadorOrganizadoresNacionales",
        numeroSeguro(
          indicadores.organizadores_nacionales
        ).toLocaleString("es-NI")
      );

      actualizarTexto(
        "indicadorVicecoordinadoresSede",
        numeroSeguro(
          indicadores.vicecoordinadores_sede
        ).toLocaleString("es-NI")
      );

      actualizarTexto(
        "indicadorEquiposAbiertos",
        numeroSeguro(
          indicadores.equipos_abiertos
        ).toLocaleString("es-NI")
      );

      actualizarTexto(
        "resumenEquiposConformados",
        numeroSeguro(
          indicadores.equipos_conformados
        ).toLocaleString("es-NI")
      );

      actualizarTexto(
        "indicadorPorcentajeConformacion",
        numeroSeguro(
          indicadores.porcentaje_conformacion
        ).toLocaleString(
          "es-NI",
          {
            minimumFractionDigits: 1,
            maximumFractionDigits: 1
          }
        ) + " %"
      );
    }


    function crearGraficoCircular(
      nombre,
      canvasId,
      mensajeId,
      registros
    ) {
      destruirGrafico(nombre);

      const lista = Array.isArray(registros)
        ? registros
        : [];

      const etiquetas = lista.map(
        item => item.nombre
      );

      const valores = lista.map(
        item => numeroSeguro(item.total)
      );

      const tieneDatos = valores.some(
        valor => valor > 0
      );

      alternarSinDatos(
        canvasId,
        mensajeId,
        tieneDatos
      );

      if (!tieneDatos) {
        return;
      }

      graficos[nombre] = new Chart(
        document
          .getElementById(canvasId)
          .getContext("2d"),
        {
          type: "doughnut",
          data: {
            labels: etiquetas,
            datasets: [
              {
                data: valores,
                borderWidth: 2
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "58%",
            plugins: {
              legend: {
                position: "bottom",
                labels: {
                  usePointStyle: true,
                  padding: 18
                }
              },
              datalabels: {
                display: function (context) {
                  return numeroSeguro(
                    context.dataset.data[
                      context.dataIndex
                    ]
                  ) > 0;
                },
                color: "#ffffff",
                font: {
                  weight: "bold"
                },
                formatter: function (valor) {
                  return numeroSeguro(
                    valor
                  ).toLocaleString("es-NI");
                }
              }
            }
          }
        }
      );
    }

    function dividirEtiqueta(
        texto,
        maximoCaracteres = 28,
        maximoLineas = 3
        ) {
        const contenido = String(
            texto || ""
        ).trim();

        if (!contenido) {
            return [""];
        }

        const palabras = contenido.split(/\s+/);
        const lineas = [];
        let lineaActual = "";

        palabras.forEach(
            function (palabra) {
            const lineaPropuesta = (
                lineaActual
                ? lineaActual + " " + palabra
                : palabra
            );

            if (
                lineaPropuesta.length <= maximoCaracteres
            ) {
                lineaActual = lineaPropuesta;
                return;
            }

            if (lineaActual) {
                lineas.push(
                lineaActual
                );
            }

            lineaActual = palabra;
            }
        );

        if (lineaActual) {
            lineas.push(
            lineaActual
            );
        }

        if (
            lineas.length > maximoLineas
        ) {
            const lineasVisibles = lineas.slice(
            0,
            maximoLineas
            );

            const ultimaPosicion = (
            lineasVisibles.length - 1
            );

            let ultimaLinea = lineasVisibles[
            ultimaPosicion
            ];

            if (
            ultimaLinea.length
            > maximoCaracteres - 3
            ) {
            ultimaLinea = ultimaLinea.slice(
                0,
                maximoCaracteres - 3
            );
            }

            lineasVisibles[
            ultimaPosicion
            ] = ultimaLinea + "...";

            return lineasVisibles;
        }

        return lineas;
    }


    function crearGraficoBarras(
        nombre,
        canvasId,
        mensajeId,
        registros
        ) {
        destruirGrafico(
            nombre
        );

        const lista = Array.isArray(
            registros
        )
            ? registros
            : [];

        const etiquetasOriginales = lista.map(
            function (item) {
            return String(
                item.nombre || ""
            );
            }
        );

        const etiquetas = etiquetasOriginales.map(
            function (etiqueta) {
            return dividirEtiqueta(
                etiqueta,
                28,
                3
            );
            }
        );

        const valores = lista.map(
            function (item) {
            return numeroSeguro(
                item.total
            );
            }
        );

        const tieneDatos = valores.some(
            function (valor) {
            return valor > 0;
            }
        );

        alternarSinDatos(
            canvasId,
            mensajeId,
            tieneDatos
        );

        if (!tieneDatos) {
            return;
        }

        const canvas = document.getElementById(
            canvasId
        );

        const contenedor = canvas.parentElement;

        const alturaCalculada = Math.max(
            360,
            lista.length * 58
        );

        contenedor.style.height = (
            alturaCalculada + "px"
        );

        graficos[nombre] = new Chart(
            canvas.getContext("2d"),
            {
            type: "bar",

            data: {
                labels: etiquetas,

                datasets: [
                {
                    label: "Cantidad",
                    data: valores,
                    borderRadius: 6,
                    maxBarThickness: 42
                }
                ]
            },

            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,

                layout: {
                padding: {
                    top: 8,
                    right: 48,
                    bottom: 8,
                    left: 4
                }
                },

                scales: {
                x: {
                    beginAtZero: true,
                    grace: "12%",

                    ticks: {
                    precision: 0
                    }
                },

                y: {
                    grid: {
                    display: false
                    },

                    ticks: {
                    autoSkip: false,
                    font: {
                        size: 11
                    }
                    }
                }
                },

                plugins: {
                legend: {
                    display: false
                },

                tooltip: {
                    callbacks: {
                    title: function (elementos) {
                        if (
                        !elementos
                        || elementos.length === 0
                        ) {
                        return "";
                        }

                        const indice = elementos[
                        0
                        ].dataIndex;

                        return etiquetasOriginales[
                        indice
                        ] || "";
                    },

                    label: function (context) {
                        return (
                        "Cantidad: "
                        + numeroSeguro(
                            context.parsed.x
                            ).toLocaleString(
                            "es-NI"
                            )
                        );
                    }
                    }
                },

                datalabels: {
                    display: function (context) {
                    return numeroSeguro(
                        context.dataset.data[
                        context.dataIndex
                        ]
                    ) > 0;
                    },

                    anchor: "end",
                    align: "end",
                    clamp: true,
                    clip: false,
                    color: "#495057",

                    font: {
                    weight: "bold",
                    size: 11
                    },

                    formatter: function (valor) {
                    return numeroSeguro(
                        valor
                    ).toLocaleString(
                        "es-NI"
                    );
                    }
                }
                }
            }
            }
        );
        }


    function obtenerConfiguracionTabla(tipo) {
      const configuraciones = {
        sedes: {
          cuerpo: "tablaSedesCuerpo",
          info: "infoSedes",
          paginacion: "paginacionSedes",
          columnas: 4
        },
        departamentos: {
          cuerpo: "tablaDepartamentosCuerpo",
          info: "infoDepartamentos",
          paginacion: "paginacionDepartamentos",
          columnas: 3
        },
        municipios: {
          cuerpo: "tablaMunicipiosCuerpo",
          info: "infoMunicipios",
          paginacion: "paginacionMunicipios",
          columnas: 4
        }
      };

      return configuraciones[tipo];
    }


    function crearBotonPagina(
      contenido,
      pagina,
      activo,
      deshabilitado,
      callback
    ) {
      const item = document.createElement("li");

      item.className = "page-item";

      if (activo) {
        item.classList.add("active");
      }

      if (deshabilitado) {
        item.classList.add("disabled");
      }

      const boton = document.createElement("button");

      boton.type = "button";
      boton.className = "page-link";
      boton.innerHTML = contenido;

      boton.addEventListener(
        "click",
        function () {
          if (
            !activo
            && !deshabilitado
          ) {
            callback(pagina);
          }
        }
      );

      item.appendChild(boton);

      return item;
    }


    function construirFilaTabla(
      tipo,
      registro,
      posicion
    ) {
      if (tipo === "sedes") {
        return (
          '<tr>'
          + '<td><span class="dashboard-tabla-posicion">'
          + posicion
          + '</span></td>'
          + '<td>'
          + '<div class="fw-semibold">'
          + escaparHtml(
              registro.institucion
              || "Sin institución"
            )
          + '</div>'
          + '<div class="small text-body-secondary">'
          + escaparHtml(
              registro.institucion_nombre
              || ""
            )
          + '</div>'
          + '</td>'
          + '<td>'
          + '<div class="fw-semibold">'
          + escaparHtml(
              registro.nombre
              || "Sin sede"
            )
          + '</div>'
          + (
              registro.siglas
              ? (
                  '<div class="small text-body-secondary">'
                  + escaparHtml(registro.siglas)
                  + '</div>'
                )
              : ""
            )
          + '</td>'
          + '<td class="text-end">'
          + '<span class="dashboard-tabla-cantidad">'
          + numeroSeguro(
              registro.total
            ).toLocaleString("es-NI")
          + '</span>'
          + '</td>'
          + '</tr>'
        );
      }

      if (tipo === "municipios") {
        return (
          '<tr>'
          + '<td><span class="dashboard-tabla-posicion">'
          + posicion
          + '</span></td>'
          + '<td>'
          + escaparHtml(
              registro.departamento
              || "Sin departamento"
            )
          + '</td>'
          + '<td class="fw-semibold">'
          + escaparHtml(
              registro.nombre
              || "Sin municipio"
            )
          + '</td>'
          + '<td class="text-end">'
          + '<span class="dashboard-tabla-cantidad">'
          + numeroSeguro(
              registro.total
            ).toLocaleString("es-NI")
          + '</span>'
          + '</td>'
          + '</tr>'
        );
      }

      return (
        '<tr>'
        + '<td><span class="dashboard-tabla-posicion">'
        + posicion
        + '</span></td>'
        + '<td class="fw-semibold">'
        + escaparHtml(
            registro.nombre
            || "Sin departamento"
          )
        + '</td>'
        + '<td class="text-end">'
        + '<span class="dashboard-tabla-cantidad">'
        + numeroSeguro(
            registro.total
          ).toLocaleString("es-NI")
        + '</span>'
        + '</td>'
        + '</tr>'
      );
    }


    function renderizarTabla(tipo) {
      const tabla = tablas[tipo];
      const config = obtenerConfiguracionTabla(tipo);

      const cuerpo = document.getElementById(
        config.cuerpo
      );

      const info = document.getElementById(
        config.info
      );

      const paginacion = document.getElementById(
        config.paginacion
      );

      const total = tabla.filtrados.length;

      const totalPaginas = Math.max(
        Math.ceil(total / tabla.porPagina),
        1
      );

      tabla.pagina = Math.min(
        tabla.pagina,
        totalPaginas
      );

      const inicio = (
        tabla.pagina - 1
      ) * tabla.porPagina;

      const fin = Math.min(
        inicio + tabla.porPagina,
        total
      );

      const registros = tabla.filtrados.slice(
        inicio,
        fin
      );

      cuerpo.innerHTML = "";

      if (!registros.length) {
        cuerpo.innerHTML = (
          '<tr>'
          + '<td colspan="'
          + config.columnas
          + '" class="dashboard-tabla-vacia">'
          + '<i class="fa-solid fa-inbox '
          + 'fa-2x text-body-secondary mb-3 d-block"></i>'
          + '<div class="fw-semibold">'
          + 'No hay registros para mostrar'
          + '</div>'
          + '</td>'
          + '</tr>'
        );

        info.textContent = "Mostrando 0 registros";
        paginacion.innerHTML = "";

        return;
      }

      registros.forEach(
        function (
          registro,
          indice
        ) {
          cuerpo.insertAdjacentHTML(
            "beforeend",
            construirFilaTabla(
              tipo,
              registro,
              inicio + indice + 1
            )
          );
        }
      );

      info.textContent = (
        "Mostrando "
        + (inicio + 1)
        + " a "
        + fin
        + " de "
        + total
        + " registros"
      );

      paginacion.innerHTML = "";

      paginacion.appendChild(
        crearBotonPagina(
          '<i class="fa-solid fa-chevron-left"></i>',
          tabla.pagina - 1,
          false,
          tabla.pagina === 1,
          function (pagina) {
            tabla.pagina = pagina;
            renderizarTabla(tipo);
          }
        )
      );

      let paginaInicio = Math.max(
        tabla.pagina - 2,
        1
      );

      let paginaFin = Math.min(
        paginaInicio + 4,
        totalPaginas
      );

      paginaInicio = Math.max(
        paginaFin - 4,
        1
      );

      for (
        let pagina = paginaInicio;
        pagina <= paginaFin;
        pagina += 1
      ) {
        paginacion.appendChild(
          crearBotonPagina(
            pagina,
            pagina,
            pagina === tabla.pagina,
            false,
            function (paginaSeleccionada) {
              tabla.pagina = paginaSeleccionada;
              renderizarTabla(tipo);
            }
          )
        );
      }

      paginacion.appendChild(
        crearBotonPagina(
          '<i class="fa-solid fa-chevron-right"></i>',
          tabla.pagina + 1,
          false,
          tabla.pagina === totalPaginas,
          function (pagina) {
            tabla.pagina = pagina;
            renderizarTabla(tipo);
          }
        )
      );
    }


    function cargarDatosTabla(
      tipo,
      registros
    ) {
      tablas[tipo].datos = Array.isArray(registros)
        ? registros
        : [];

      tablas[tipo].filtrados = [
        ...tablas[tipo].datos
      ];

      tablas[tipo].pagina = 1;

      renderizarTabla(tipo);
    }


    function filtrarTabla(
      tipo,
      termino
    ) {
      const texto = String(
        termino || ""
      )
        .trim()
        .toLocaleLowerCase("es");

      tablas[tipo].filtrados = tablas[tipo].datos.filter(
        function (registro) {
          const contenido = [
            registro.nombre,
            registro.siglas,
            registro.institucion,
            registro.institucion_nombre,
            registro.departamento
          ]
            .filter(Boolean)
            .join(" ")
            .toLocaleLowerCase("es");

          return contenido.includes(texto);
        }
      );

      tablas[tipo].pagina = 1;

      renderizarTabla(tipo);
    }


    function actualizarContenido(datos) {
      const graficosDatos = datos.graficos || {};
      const tablasDatos = datos.tablas || {};

      crearGraficoCircular(
        "sexos",
        "graficoSexos",
        "sinDatosSexos",
        graficosDatos.sexos
      );

      crearGraficoCircular(
        "etnias",
        "graficoEtnias",
        "sinDatosEtnias",
        graficosDatos.etnias
      );

      crearGraficoBarras(
        "retos",
        "graficoRetos",
        "sinDatosRetos",
        graficosDatos.retos
      );

      crearGraficoBarras(
        "categorias",
        "graficoCategorias",
        "sinDatosCategorias",
        graficosDatos.categorias
      );

      cargarDatosTabla(
        "sedes",
        tablasDatos.sedes
      );

      cargarDatosTabla(
        "departamentos",
        tablasDatos.departamentos
      );

      cargarDatosTabla(
        "municipios",
        tablasDatos.municipios
      );
    }


    async function cargarDashboard() {
      ocultarError();

      if (solicitudDashboard) {
        solicitudDashboard.abort();
      }

      const controlador = new AbortController();

      solicitudDashboard = controlador;

      mostrarCarga();

      try {
        const respuesta = await fetch(
          urlDatos
          + "?"
          + obtenerParametros().toString(),
          {
            headers: {
              "X-Requested-With": "XMLHttpRequest"
            },
            signal: controlador.signal
          }
        );

        const datos = await respuesta.json();

        if (
          !respuesta.ok
          || !datos.ok
        ) {
          throw new Error(
            datos.mensaje
            || "No fue posible consultar las estadísticas."
          );
        }

        actualizarIndicadores(datos);
        actualizarContenido(datos);

      } catch (error) {
        if (error.name !== "AbortError") {
          mostrarError(
            error.message
            || "No fue posible cargar el dashboard."
          );
        }

      } finally {
        if (
          solicitudDashboard === controlador
        ) {
          solicitudDashboard = null;
          ocultarCarga();
        }
      }
    }


    async function cargarSedes(
      valorSeleccionado = ""
    ) {
      if (
        !filtroInstitucion
        || !filtroSede
        || filtroSede.tagName !== "SELECT"
      ) {
        return;
      }

      const institucion = (
        filtroInstitucion.value
        || ""
      ).trim();

      if (solicitudSedes) {
        solicitudSedes.abort();
      }

      const controlador = new AbortController();

      solicitudSedes = controlador;

      filtroSede.innerHTML = (
        '<option value="">'
        + 'Todas las sedes autorizadas'
        + '</option>'
      );

      filtroSede.disabled = true;

      if ($) {
        $(filtroSede)
          .prop("disabled", true)
          .val("")
          .trigger("change.select2");
      }

      if (!institucion) {
        solicitudSedes = null;
        return;
      }

      try {
        const parametros = new URLSearchParams({
          institucion: institucion
        });

        const respuesta = await fetch(
          urlSedes
          + "?"
          + parametros.toString(),
          {
            headers: {
              "X-Requested-With": "XMLHttpRequest"
            },
            signal: controlador.signal
          }
        );

        const datos = await respuesta.json();

        if (
          !respuesta.ok
          || !datos.ok
        ) {
          throw new Error(
            datos.mensaje
            || "No fue posible consultar las sedes."
          );
        }

        const resultados = Array.isArray(
          datos.resultados
        )
          ? datos.resultados
          : [];

        resultados.forEach(
          function (sede) {
            const opcion = document.createElement(
              "option"
            );

            opcion.value = sede.id;
            opcion.textContent = sede.text;

            filtroSede.appendChild(opcion);
          }
        );

        const existe = resultados.some(
          function (sede) {
            return (
              String(sede.id)
              === String(valorSeleccionado)
            );
          }
        );

        const valorFinal = existe
          ? valorSeleccionado
          : "";

        filtroSede.disabled = false;
        filtroSede.value = valorFinal;

        if ($) {
          $(filtroSede)
            .prop("disabled", false)
            .val(valorFinal)
            .trigger("change.select2");
        }

      } catch (error) {
        if (error.name !== "AbortError") {
          mostrarError(
            error.message
            || "No fue posible cargar las sedes."
          );
        }

      } finally {
        if (
          solicitudSedes === controlador
        ) {
          solicitudSedes = null;
        }
      }
    }


    function registrarEventos() {
      if (formulario) {
        formulario.addEventListener(
          "submit",
          function (evento) {
            evento.preventDefault();
          }
        );
      }

      if (
        filtroInstitucion
        && filtroInstitucion.tagName === "SELECT"
      ) {
        if ($) {
          $(filtroInstitucion)
            .off("change.dashboard")
            .on(
              "change.dashboard",
              async function () {
                await cargarSedes("");
                await cargarDashboard();
              }
            );
        }
      }

      if (
        filtroSede
        && filtroSede.tagName === "SELECT"
        && $
      ) {
        $(filtroSede)
          .off("change.dashboard")
          .on(
            "change.dashboard",
            cargarDashboard
          );
      }

      if (
        filtroEdicion
        && filtroEdicion.tagName === "SELECT"
        && $
      ) {
        $(filtroEdicion)
          .off("change.dashboard")
          .on(
            "change.dashboard",
            cargarDashboard
          );
      }

      const buscadores = {
        buscarSedes: "sedes",
        buscarDepartamentos: "departamentos",
        buscarMunicipios: "municipios"
      };

      Object.entries(buscadores).forEach(
        function (
          [id, tipo]
        ) {
          const campo = document.getElementById(id);

          if (campo) {
            campo.addEventListener(
              "input",
              function () {
                filtrarTabla(
                  tipo,
                  this.value
                );
              }
            );
          }
        }
      );
    }


    async function iniciarDashboard() {
      inicializarSelect2Dashboard();
      registrarEventos();

      const sedeInicial = (
        filtroSede
        && filtroSede.tagName === "SELECT"
        ? (
            filtroSede.dataset.valorInicial
            || filtroSede.value
            || ""
          )
        : ""
      );

      if (
        filtroInstitucion
        && filtroInstitucion.value
        && filtroSede
        && filtroSede.tagName === "SELECT"
      ) {
        await cargarSedes(sedeInicial);

      } else if (
        filtroSede
        && filtroSede.tagName === "SELECT"
      ) {
        filtroSede.disabled = true;

        if ($) {
          $(filtroSede)
            .prop("disabled", true)
            .trigger("change.select2");
        }
      }

      await cargarDashboard();
    }


    iniciarDashboard();
  }
);
