# API

На данный момент существует 2 метода. API доступен по адресу [https://d2info.happyv0dka.cloud/api](/api)

### dailyRotations

#### Путь

`/dailyrotations`

### weeklyRotations

#### Путь

`/weeklyrotations`

#### Возвращаемые данные

<table>
<thead>
  <tr>
    <th>Поле</th>
    <th>Тип</th>
  </tr>
</thead>
<tbody>
  <tr>
    <td>Response</td>
    <td>массив JSON</td>
  </tr>
</tbody>
</table>

#### Элемент Response

<table>
<thead>
  <tr>
    <th>Поле</th>
    <th>Тип</th>
    <th>Описание</th>
  </tr>
</thead>
<tbody>
  <tr>
    <td>name</td>
    <td>str</td>
    <td>Имя поля</td>
  </tr>
  <tr>
    <td>items</td>
    <td>массив JSON</td>
    <td>Данные элемента</td>
  </tr>
</tbody>
</table>

#### item

<table>
<thead>
  <tr>
    <th>Поле</th>
    <th>Тип</th>
    <th>Описание</th>
  </tr>
</thead>
<tbody>
  <tr>
    <td>icon</td>
    <td>str</td>
    <td>ссылка на иконку (опционально)</td>
  </tr>
  <tr>
    <td>name</td>
    <td>str</td>
    <td>Имя элемента</td>
  </tr>
  <tr>
    <td>description</td>
    <td>str</td>
    <td>Описание элемента</td>
  </tr>
</tbody>
</table>
